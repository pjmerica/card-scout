#!/usr/bin/env python3
"""
Site health check (runs as the last CI step, even when earlier steps failed).

Reads the fresh site/cards.json and the CI step outcomes. With --issue (in CI) it keeps ONE
GitHub issue titled "Site health: needs attention": opens it when something is wrong (GitHub
emails the repo owner), updates/comments when the problems change, closes it when all pass.
Locally: `python tools/health.py` just prints the report.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
TITLE = "Site health: needs attention"

# Thresholds: well below a normal run (FM ~237, DoC ~84, Rakuten ~100, news ~140, 24/25 sources)
MIN = {"Frequent Miler: Best Card Offers": 150, "Doctor of Credit: Best Sign-up Bonuses": 40,
       "Rakuten cash-back rates": 70}
MIN_NEWS = 50
MIN_SOURCE_SHARE = 0.80


def check() -> tuple[list[str], list[str]]:
    problems, notes = [], []
    for step in ("TESTS", "SCRAPE", "SMOKE"):
        outcome = os.environ.get(f"{step}_OUTCOME", "")
        if outcome and outcome != "success":
            problems.append(f"CI step **{step.lower()}** {outcome}")
    path = SITE / "cards.json"
    if not path.exists():
        problems.append("`site/cards.json` was not produced (the scrape crashed before writing output)")
        return problems, notes
    d = json.loads(path.read_text(encoding="utf-8"))
    c = d["counts"]
    by_name = {s["name"]: s for s in d["sources"]}
    for name, floor in MIN.items():
        s = by_name.get(name)
        n = s["count"] if s else 0
        if n < floor:
            problems.append(f"**{name}** returned {n} (expected {floor}+). Its page layout may have changed: "
                            f"see HANDOFF.md §4 for the parser")
    if c["news"] < MIN_NEWS:
        problems.append(f"Only {c['news']} news posts (normally ~140)")
    # Reddit stays off until API keys are added, so it never counts against health
    srcs = [s for s in d["sources"] if not s["name"].startswith("Reddit (needs")]
    ok = sum(1 for s in srcs if s["ok"])
    if ok < MIN_SOURCE_SHARE * len(srcs):
        down = [s["name"] for s in srcs if not s["ok"]][:15]
        problems.append(f"Only {ok}/{len(srcs)} sources online. Down: {', '.join(down)}")
    if not c.get("runs_tracked"):
        notes.append("History was reset (previous history.json not loaded); value-up/elevated signals restart.")
    return problems, notes


def render(problems: list[str], notes: list[str]) -> str:
    repo, run = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", "")
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sig = hashlib.sha1("\n".join(sorted(problems)).encode()).hexdigest()[:12]
    lines = [f"Automatic check from the site build ({when}). This issue closes itself when the next build passes.", ""]
    if run:
        lines += [f"Run: https://github.com/{repo}/actions/runs/{run}", ""]
    lines += ["### Problems"] + [f"- {p}" for p in problems]
    if notes:
        lines += ["", "### Notes"] + [f"- {n}" for n in notes]
    lines += ["", "The live site keeps its last good version whenever tests fail.", "", f"<!-- health-sig: {sig} -->"]
    return "\n".join(lines)


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def sync_issue(problems: list[str], notes: list[str]) -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    r = gh("issue", "list", "--repo", repo, "--state", "open", "--search", f'"{TITLE}" in:title',
           "--json", "number,title,body")
    issues = [i for i in json.loads(r.stdout or "[]") if i["title"] == TITLE]
    body = render(problems, notes)
    if problems:
        if not issues:
            out = gh("issue", "create", "--repo", repo, "--title", TITLE, "--body", body)
            print("opened issue:", out.stdout.strip() or out.stderr.strip())
            return
        num, old = issues[0]["number"], issues[0]["body"] or ""
        changed = ("health-sig: " + body.rsplit("health-sig: ", 1)[-1]) not in old
        gh("issue", "edit", str(num), "--repo", repo, "--body", body)
        if changed:
            gh("issue", "comment", str(num), "--repo", repo, "--body",
               "The problem list changed:\n\n" + "\n".join(f"- {p}" for p in problems))
        print(f"updated issue #{num} (changed={changed})")
    else:
        for i in issues:
            gh("issue", "close", str(i["number"]), "--repo", repo, "--comment",
               f"All checks pass again ({datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}). Closing automatically.")
            print(f"closed issue #{i['number']}")


def main() -> int:
    problems, notes = check()
    print("HEALTH:", "needs attention" if problems else "OK")
    for p in problems:
        print("  problem:", p)
    for n in notes:
        print("  note:", n)
    if "--issue" in sys.argv:
        try:
            sync_issue(problems, notes)
        except Exception as ex:  # noqa: BLE001 - never fail the build because of the issue sync
            print("issue sync failed:", ex)
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("### Site health: " + ("needs attention" if problems else "OK") + "\n")
            f.writelines(f"- {p}\n" for p in problems + notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
