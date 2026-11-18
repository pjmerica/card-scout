# Card Scout

The best **credit card sign-up offers**, ranked by estimated first-year value, plus **card-linked shopping offers**,
**card and points news**, and **Rakuten cash-back rates** for clothing and department stores. GitHub Actions
re-scrapes every 4 hours and redeploys to GitHub Pages:

**https://pjmerica.github.io/card-scout/**

Companion site for the deals themselves: [Deal Scout](https://pjmerica.github.io/deal-scout/)
([repo](https://github.com/pjmerica/deal-scout)). The two were one project until 2026-11-18. See [HANDOFF.md](HANDOFF.md).

## What's on the site

| Tab | What it shows |
|---|---|
| 💳 Sign-up offers | About 270 cards (personal and business). Each shows the offer, estimated first-year value, minimum spend, annual fee, why it ranks, and badges (Value up, New, Elevated, DoC pick, Targeted, Shopping perk). Filters: no fee in year 1, minimum spend of $5k or less |
| 📰 Card news & offers | Card-linked offers (Amex, Chase, Capital One), portal deals, sign-up bonus news, bank bonuses and transfer bonuses, ranked with reasons. A NEW badge marks posts that appeared since the last run |
| 💸 Cash back | Rakuten rates for about 100 clothing and department stores, with usual and highest-seen rates and an Elevated flag |
| 📋 Playbook | Evergreen guidance for stacking a portal, a card-linked offer, the right card and a promo code |
| ⚙️ How it works | The ranking formulas, plus every source with live status and item count |

## Run locally

```
pip install -r requirements.txt
python card_scout.py --open          # or double-click run_card_scout.bat
python tests/test_cards.py && node tests/smoke.js site/index.html
```

Output: `site/index.html`, `site/cards.json`, `site/offers.csv`, `site/history.json` (`site/` is gitignored; CI builds it).

## Optional: Reddit

Anonymous Reddit access is blocked. To add r/CreditCards, r/churning and r/awardtravel, create a free "script" app at
https://www.reddit.com/prefs/apps and add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` as repository secrets.
