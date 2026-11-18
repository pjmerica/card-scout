"""
Run-to-run memory. On GitHub Actions the previous history.json is downloaded from the
live Pages site (nothing is committed); locally it's read from site/history.json.

Tracks:
  offers   card name -> value series      => "Value up" (vs the highest value seen before) and "New offer"
  rakuten  store slug -> rate series      => "Elevated" (above the usual/median rate), highest seen
  news     link key -> first seen         => NEW badge (appeared since the previous run)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from feeds import fetch, normalize_link
from models import NOW, Item

DEFAULT_URL = "https://pjmerica.github.io/card-scout/history.json"
KEEP_DAYS = 45


def load(local: Path) -> dict:
    url = os.environ.get("HISTORY_URL", DEFAULT_URL)
    data = None
    if os.environ.get("GITHUB_ACTIONS") or not local.exists():
        raw = fetch(url, retries=1)
        if raw:
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
    if data is None and local.exists():
        try:
            data = json.loads(local.read_text(encoding="utf-8"))
        except ValueError:
            data = None
    data = data or {}
    for k in ("offers", "rakuten", "news"):
        data.setdefault(k, {})
    data.setdefault("runs", [])
    return data


def _is_baseline(hist: dict) -> bool:
    return not hist["runs"]


def apply_offers(hist: dict, offers: list[dict]) -> None:
    O = hist["offers"]
    baseline = _is_baseline(hist)
    for o in offers:
        key = o["name"]
        h = O.get(key)
        v = o.get("value") or 0
        o["value_up"] = o["new_offer"] = False
        o["prev_best"] = None
        if h is None:
            O[key] = {"first": NOW.isoformat(), "values": [[NOW.isoformat(), v]], "offer": o.get("offer", "")}
            o["new_offer"] = not baseline
            continue
        series = h["values"]
        prev_best = max((x for _, x in series), default=0)
        if v and prev_best and v >= prev_best * 1.10 and v - prev_best >= 50:
            o["value_up"] = True
            o["prev_best"] = prev_best
        if not series or series[-1][1] != v:
            series.append([NOW.isoformat(), v])
        h["values"] = series[-60:]
        h["offer"] = o.get("offer", "")
        h["last"] = NOW.isoformat()


def apply_rakuten(hist: dict, rates: list[dict]) -> None:
    R = hist["rakuten"]
    for r in rates:
        h = R.setdefault(r["slug"], {"rates": []})
        series = h["rates"]
        if not series or series[-1][1] != r["pct"]:
            series.append([NOW.isoformat(), r["pct"]])
        h["rates"] = series[-60:]
        vals = sorted(v for _, v in series)
        r["usual"] = vals[len(vals) // 2] if vals else r["pct"]
        r["elevated"] = len(vals) > 1 and r["pct"] > r["usual"]
        r["max_seen"] = vals[-1] if vals else r["pct"]


def apply_news(hist: dict, items: list[Item]) -> None:
    N = hist["news"]
    baseline = _is_baseline(hist)
    prev = hist["runs"][-1] if hist["runs"] else ""
    for it in items:
        k = f"sd:{it.thread_id}" if it.thread_id else normalize_link(it.link)[:200]
        h = N.get(k)
        if h is None:
            N[k] = {"first": NOW.isoformat(), "last": NOW.isoformat()}
            it.is_new = not baseline
        else:
            it.is_new = len(hist["runs"]) >= 2 and h["first"] >= prev and h["first"] != hist["runs"][0]
            h["last"] = NOW.isoformat()


def save(hist: dict, path: Path) -> None:
    cutoff = NOW - timedelta(days=KEEP_DAYS)
    hist["news"] = {k: v for k, v in hist["news"].items() if datetime.fromisoformat(v["last"]) >= cutoff}
    hist["runs"] = (hist["runs"] + [NOW.isoformat()])[-300:]
    path.write_text(json.dumps(hist, separators=(",", ":")), encoding="utf-8")
