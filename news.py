"""
Card/points news: relevance filter, category, and an explainable score.

Score = 8 + source boost
      + bonus value quoted in the title (points x POINT_VALUE_CENTS, or $ cash; award redemptions excluded)
      + "hot" words (elevated / all-time high, card-linked offers, portals, 5% categories, protections...)
      + SHOPPING_RETAILER_BONUS if a clothing/department store is named
      + engagement (blog comment count, Slickdeals votes, log-scaled)
      - 30 if the title says dead/expired;  - 6 if it fits no category ("Card & Points News")
      then x freshness decay (halves every NEWS_HALF_LIFE_DAYS)
"""
from __future__ import annotations

import math
import re

import config as C
from feeds import normalize_link
from models import Item

REL_RE = re.compile("|".join(C.CARD_RELEVANCE), re.I)
JUNK_RE = re.compile(C.CARD_JUNK, re.I)
CAT_RES = [(name, re.compile("|".join(p), re.I)) for name, p in C.CARD_CATEGORIES]
HOT_RES = [(re.compile(p, re.I), pts) for p, pts in C.CARD_HOT_TERMS.items()]
DEAD_RE = re.compile(C.CARD_DEAD_TERMS, re.I)
RETAIL_RE = re.compile(r"(?<![\w'])(?:" + "|".join(re.escape(r) for r in sorted(C.SHOPPING_RETAILERS, key=len, reverse=True))
                       + r")(?![\w'])", re.I)
AWARD_RE = re.compile(r"award|one-way|round-?trip|\bstays?\b|\bbook\b|redeem|\bfly\b|from [\d,]+k? (?:points|miles)", re.I)
POINTS_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{2,3}k|\d{2,3}K)\s*(?:bonus\s*)?(?:points|miles|pts|membership rewards|"
                       r"ultimate rewards|thankyou|avios)", re.I)
CASH_BONUS_RE = re.compile(r"\$(\d{2,4}(?:,\d{3})?)\s*(?:cash\s*)?(?:bonus|sign-?up|welcome)", re.I)
BF_RE = re.compile(r"black friday|cyber monday|cyber week|holiday", re.I)


def decay(age: float, half_life: float) -> float:
    return max(0.2, 0.5 ** (age / half_life))


def relevant(it: Item) -> bool:
    return bool(REL_RE.search(it.title)) and not JUNK_RE.search(it.title)


def score(it: Item) -> None:
    text = f"{it.title} {it.summary[:300]}"
    s = 8.0 + it.boost
    val = 0
    for m in ([] if AWARD_RE.search(it.title) else POINTS_RE.finditer(it.title)):
        raw = m.group(1).lower().replace(",", "")
        pts = int(raw[:-1]) * 1000 if raw.endswith("k") else int(raw)
        val = max(val, int(pts * C.POINT_VALUE_CENTS / 100))
    for m in CASH_BONUS_RE.finditer(it.title):
        val = max(val, int(m.group(1).replace(",", "")))
    if val:
        it.bonus_value = val
        s += min(45, val / 25)
        it.reasons.append(f"≈${val:,} bonus value")
    for rx, pts in HOT_RES:
        m = rx.search(text)
        if m:
            s += pts
            it.reasons.append(m.group(0).strip().capitalize())
    it.retailers = sorted({m.group(0).title() for m in RETAIL_RE.finditer(text)})[:4]
    if it.retailers:
        s += C.SHOPPING_RETAILER_BONUS
        it.reasons.append("Clothing/department store: " + ", ".join(it.retailers[:2]))
    if it.comments:
        s += 3 * math.log2(1 + it.comments)
    if it.votes and it.votes > 0:
        s += 6 * math.log2(1 + it.votes)
    if DEAD_RE.search(it.title):
        s -= 30
        it.warnings.append("May be expired")
    for name, rx in CAT_RES:
        if rx.search(it.title):
            it.card_category = name
            break
    if not it.card_category:
        it.card_category = "Card & Points News"
        s -= 6
    it.is_bf = bool(BF_RE.search(text))
    if len(it.sources) > 1:
        s += min(12, 4 * (len(it.sources) - 1))
        it.reasons.append(f"Found on {len(it.sources)} sources")
    seen, rr = set(), []
    for r in it.reasons:
        if r.lower() not in seen:
            seen.add(r.lower())
            rr.append(r)
    it.reasons = rr
    it.score = round(s * decay(it.age_days, C.NEWS_HALF_LIFE_DAYS), 1)


def _title_key(t: str) -> str:
    t = re.sub(r"[^a-z0-9 ]", "", t.lower())
    return " ".join(t.split()[:10])


def dedupe(items: list[Item]) -> list[Item]:
    groups: dict[str, Item] = {}
    order: list[Item] = []
    for it in items:
        keys = [k for k in (f"sd:{it.thread_id}" if it.thread_id else "", normalize_link(it.link), _title_key(it.title)) if k]
        hit = next((groups[k] for k in keys if k in groups), None)
        if hit:
            if it.source not in hit.sources:
                hit.sources.append(it.source)
            hit.votes = hit.votes if hit.votes is not None else it.votes
            hit.comments = max(hit.comments or 0, it.comments or 0) or None
            hit.boost = max(hit.boost, it.boost)
            for k in keys:
                groups.setdefault(k, hit)
            continue
        it.sources = [it.source]
        for k in keys:
            groups[k] = it
        order.append(it)
    return order


def process(raw: list[Item], max_age: float = C.MAX_AGE_DAYS) -> list[Item]:
    items = [i for i in dedupe(raw) if relevant(i) and not (i.published and i.age_days > max_age)]
    for i in items:
        score(i)
    items.sort(key=lambda x: -x.score)
    return items
