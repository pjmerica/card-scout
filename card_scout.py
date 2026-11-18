#!/usr/bin/env python3
"""
Card Scout: the best credit card sign-up offers, card-linked shopping offers, card/points
news and Rakuten cash-back rates, ranked and published as a static site.

Pipeline
  1. Gather   (in parallel)
              - Frequent Miler "Best Credit Card Offers" table (first-year value estimates)
              - Doctor of Credit "Best Current Sign Up Bonuses" list (spend, fee, elevated)
              - Rakuten cash-back rates for ~120 clothing / department stores
              - card news RSS (Doctor of Credit, TPG, OMAAT, Frequent Miler, ...) + Slickdeals searches
              - optional Reddit (needs API keys)
  2. Rank     offers by first-year value model (cards.py); news by explainable score (news.py)
  3. Remember compare with the previous run (history.py): value-up / new offers, elevated rates, NEW news
  4. Publish  site/index.html, cards.json, offers.csv, history.json

Usage:
    python card_scout.py            # full run
    python card_scout.py --open     # open the page when done
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import os
import sys
import time
import webbrowser
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests

import cards
import config as C
import history
import news
from feeds import clean_text, fetch, parse_feed
from models import NOW, Item

HERE = Path(__file__).resolve().parent
SITE = HERE / "site"
TEMPLATE = HERE / "template.html"
DEAL_SCOUT_URL = "https://pjmerica.github.io/deal-scout/"


def reddit_items() -> list[Item]:
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        return []
    ua = "card-scout/1.0 (personal card-offer tracker)"
    try:
        tok = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, secret),
                            data={"grant_type": "client_credentials"}, headers={"User-Agent": ua},
                            timeout=20).json()["access_token"]
    except Exception as ex:  # noqa: BLE001
        print(f"  ! reddit auth failed: {ex}")
        return []
    out = []
    for sub, boost in C.REDDIT_SUBS:
        try:
            r = requests.get(f"https://oauth.reddit.com/r/{sub}/hot", params={"limit": 75, "raw_json": 1},
                             headers={"Authorization": f"bearer {tok}", "User-Agent": ua}, timeout=20)
            posts = r.json()["data"]["children"]
        except Exception:  # noqa: BLE001
            continue
        for p in posts:
            d = p["data"]
            if d.get("stickied"):
                continue
            pub = datetime.fromtimestamp(d["created_utc"], timezone.utc)
            out.append(Item(title=clean_text(d["title"], 300), link="https://www.reddit.com" + d["permalink"],
                            source=f"r/{sub}", boost=boost, summary=clean_text(d.get("selftext", ""), 300),
                            votes=d.get("score"), comments=d.get("num_comments"), published=pub.isoformat(),
                            age_days=(NOW - pub).total_seconds() / 86400))
        time.sleep(1)
    return out



def sd_url(q: str) -> str:
    """Slickdeals search URL; multi-word queries are quoted for a phrase match ("free people" otherwise
    matched any post with both words)."""
    return C.SLICKDEALS_SEARCH_URL.format(q=quote_plus(f'"{q}"' if " " in q else q))


def gather_news() -> tuple[list[Item], list[dict]]:
    jobs = [(f["url"], f["name"], f.get("boost", 0)) for f in C.FEEDS]
    jobs += [(sd_url(q), f"Slickdeals: {q}", 0) for q in C.SLICKDEALS_QUERIES]
    items, status = [], []

    def run(job):
        url, name, boost = job
        raw = fetch(url)
        if raw is None:
            return name, url, None
        try:
            return name, url, parse_feed(raw, name, "card", boost)
        except Exception as ex:  # noqa: BLE001
            print(f"  ! parse error {name}: {ex}")
            return name, url, None

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for name, url, res in ex.map(run, jobs):
            status.append({"name": name, "url": url, "kind": "news", "ok": res is not None, "count": len(res or [])})
            if res:
                items.extend(res)
    r = reddit_items()
    items.extend(r)
    status.append({"name": "Reddit" if r else "Reddit (needs API keys)",
                   "url": "https://www.reddit.com/prefs/apps", "kind": "news", "ok": bool(r), "count": len(r)})
    print(f"  news: {len(items)} posts from {sum(s['ok'] for s in status)}/{len(status)} feeds")
    return items, status


def gather_offers() -> tuple[list[dict], list[dict]]:
    offers, st = cards.best_card_offers()
    print(f"  offers: {st['fm']} Frequent Miler, {st['doc']} Doctor of Credit -> {len(offers)} ranked")
    return offers, [
        {"name": "Frequent Miler: Best Card Offers", "url": cards.FM_URL, "kind": "offers", "ok": st["fm"] > 0, "count": st["fm"]},
        {"name": "Doctor of Credit: Best Sign-up Bonuses", "url": cards.DOC_URL, "kind": "offers", "ok": st["doc"] > 0, "count": st["doc"]},
    ]


def gather_rakuten() -> tuple[list[dict], list[dict]]:
    rates = cards.rakuten_rates()
    print(f"  rakuten: {len(rates)} store rates")
    return rates, [{"name": "Rakuten cash-back rates", "url": "https://www.rakuten.com/stores/all", "kind": "cash back",
                    "ok": bool(rates), "count": len(rates)}]


def apply_offer_history_signals(offers: list[dict]) -> None:
    for o in offers:
        if o.get("value_up"):
            o["score"] = round(o["score"] + 10, 1)
            o["reasons"].insert(1, f"Value up from ${o['prev_best']:,} (best seen before)")
        if o.get("new_offer"):
            o["score"] = round(o["score"] + 4, 1)
            o["reasons"].insert(1, "New offer since the last check")
    offers.sort(key=lambda x: -x["score"])


def write_outputs(offers, rates, items, status, hist) -> Path:
    SITE.mkdir(exist_ok=True)
    data = {
        "generated": NOW.isoformat(),
        "counts": {
            "offers": len(offers), "personal": sum(1 for o in offers if not o["business"]),
            "business": sum(1 for o in offers if o["business"]), "news": len(items),
            "rakuten": len(rates), "elevated": sum(1 for r in rates if r.get("elevated")),
            "value_up": sum(1 for o in offers if o.get("value_up")), "new_news": sum(1 for i in items if i.is_new),
            "sources_ok": sum(1 for s in status if s["ok"]), "sources_total": len(status),
            "runs_tracked": len(hist.get("runs", [])),
        },
        "offers": offers,
        "rakuten": rates,
        "news": [{k: v for k, v in asdict(i).items() if k not in ("boost", "feed_tags", "thread_id", "price",
                                                                   "staff_pick", "expires", "kind")}
                 for i in items[:400]],
        "sources": status,
        "playbook": [{"title": t, "body": b} for t, b in C.PLAYBOOK],
        "deal_scout_url": DEAL_SCOUT_URL,
    }
    (SITE / "cards.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    cols = ["score", "name", "business", "offer", "value", "value_is_estimate", "spend", "months", "annual_fee",
            "fee_waived", "doc_pick", "elevated", "value_up", "new_offer", "targeted", "clothing_perk", "reasons", "link"]
    with open(SITE / "offers.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for o in offers:
            w.writerow(["; ".join(o.get(c) or []) if c == "reasons" else o.get(c) for c in cols])
    page = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = SITE / "index.html"
    out.write_text(page, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    history.save(hist, SITE / "history.json")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--open", action="store_true", help="open the page when done")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    hist = history.load(SITE / "history.json")
    print(f"History: {len(hist['offers'])} offers, {len(hist['rakuten'])} Rakuten stores, {len(hist['runs'])} runs")
    print("Gathering…")
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        fo, fr, fn = ex.submit(gather_offers), ex.submit(gather_rakuten), ex.submit(gather_news)
        offers, st_o = fo.result()
        rates, st_r = fr.result()
        raw, st_n = fn.result()
    status = st_o + st_r + st_n
    items = news.process(raw)
    history.apply_offers(hist, offers)
    apply_offer_history_signals(offers)
    history.apply_rakuten(hist, rates)
    history.apply_news(hist, items)
    out = write_outputs(offers, rates, items, status, hist)

    print(f"\nDone in {time.time() - t0:.0f}s: {len(offers)} offers, {len(rates)} Rakuten rates, {len(items)} news posts")
    print("\nTop personal card offers:")
    for o in [o for o in offers if not o["business"]][:8]:
        print(f"  {o['score']:5.1f}  {o['name'][:50]:50} ${o['value'] or 0:>5,}  {' · '.join(o['reasons'][1:3])}")
    print("\nTop business card offers:")
    for o in [o for o in offers if o["business"]][:4]:
        print(f"  {o['score']:5.1f}  {o['name'][:50]:50} ${o['value'] or 0:>5,}")
    print("\nBest Rakuten rates:")
    print("  " + ", ".join(f"{r['store']} {r['rate']}" for r in rates[:12]))
    print("\nTop card news:")
    for i in items[:8]:
        print(f"  {i.score:5.1f}  [{i.card_category}] {i.title[:90]}")
    print(f"\nPage: {out}")
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
