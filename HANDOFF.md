# Card Scout: handoff

**Written:** 2026-11-18 · **Owner:** pjmerica · **Local path:** `C:\Users\pjmer\Documents\card-scout`
**Repo:** https://github.com/pjmerica/card-scout · **Live:** https://pjmerica.github.io/card-scout/

Everything you need to keep this running, change it, or extend it.

> **Read first: the owner's decisions**
> - **2026-11-18: runs until January 17, 2027, no keepalive.** Enforced by the `guard` job in `cards.yml` (`END_DATE`):
>   scheduled runs do nothing after that date, while manual runs and pushes still work. GitHub would also disable the schedule
>   60 days after the last commit. To extend, change `END_DATE` (ask the owner first).
> - **2026-11-18: cards stay separate from Deal Scout.** The only link is Deal Scout reading this site's `cards.json` for badges (§4b).
> - Deferred by the owner: parsing their own Amex/Chase offers (§8). Ask before starting.
> - Deal Scout's `HANDOFF.md` has the shared lessons (Windows, Shopify throttling, heredoc pitfalls) and `tools/shots.js`,
>   a real-browser check (headless Chrome) that screenshots **both** sites. Use it after any UI change.

---

## 1. What this is and where it came from

Card Scout ranks credit card **sign-up offers**, lists **card-linked shopping offers and card/points news**, and
tracks **Rakuten cash-back rates** for clothing and department stores. Until 2026-11-18 it was part of
**Deal Scout** (`Documents\deal-scout`, https://github.com/pjmerica/deal-scout), which now covers only Black Friday
product deals. The user asked for the card material to move to its own folder and repo. The sites link to each other.

What moved here from Deal Scout: `cards.py` (Frequent Miler, Doctor of Credit, Rakuten), the card news feeds,
the card Slickdeals searches, the card news scoring (formerly `scoring.score_card`), the Rakuten store list, the card
playbook, and the Credit cards / Cash back / Playbook tabs. Deal Scout's brand-sale cards no longer show Rakuten rates.

The user's interests: **clothing first** (card-linked offers at clothing and department stores rank higher),
Black Friday timing, and offers reachable with holiday spending.

---

## 2. Run, test, deploy

| Task | Command / place |
|---|---|
| Run locally | `py -X utf8 card_scout.py --open` (or `run_card_scout.bat`). Takes about 20 s |
| Tests | `py -X utf8 tests/test_cards.py` (12 logic tests) · `node tests/smoke.js site/index.html` (renders every tab and filter against fresh data, then clicks every tab, chip and button; fails on a throw, empty output, `undefined` or `NaN`) |
| Deploy | `.github/workflows/cards.yml`: on push to `main`, every 4 h (`43 */4 * * *`), or manually (`gh workflow run cards.yml`). Steps: tests → scrape → smoke test → job summary → health (always) → Pages deploy. **A failing test or smoke test blocks the deploy**, so the live site keeps its last good version |
| Health issue | `tools/health.py` (§4c). Test the alert with `gh workflow run cards.yml -f health_test=true`; the next normal run closes the issue |
| Pages | Source is "GitHub Actions" (`build_type=workflow`). `site/` is gitignored, and nothing generated is committed |
| Secrets | Optional `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` |

Windows notes: use `py`, not `python`. Pass `-X utf8` or the console's cp1252 encoding crashes on characters like ‑ and ®.
The script also reconfigures stdout itself. `py -I` (isolated) ignores `PYTHONIOENCODING`.

---

## 3. Code map

| File | Role |
|---|---|
| `card_scout.py` | Orchestrator. Gathers offers, Rakuten and news in parallel threads, applies history, writes `site/` |
| `cards.py` | `parse_fm()`, `parse_doc()`, `best_card_offers()` (merge + value model + score), `rakuten_rates()` |
| `news.py` | News relevance filter, category, explainable score, de-duplication |
| `history.py` | Run-to-run memory (offers, Rakuten, news), loaded from the live site |
| `feeds.py` | HTTP session (browser UA, honors `Retry-After` up to `max_wait`), `fetch_head` (first chunk only), RSS/Atom parser |
| `models.py` | `Item` dataclass for news posts |
| `config.py` | **All the knobs**: feeds, Slickdeals queries, relevance and junk regexes, categories, hot-word weights, shopping retailers, Rakuten store list, playbook text |
| `template.html` | The page. `card_scout.py` replaces `/*__DATA__*/null` with the JSON payload |
| `tests/` | `test_cards.py`, `smoke.js` (renders every tab, then clicks every control) |
| `tools/health.py` | Breakage alerts (the self-closing health issue, §4c) |

---

## 4. Data sources: how each is read and how it can break

### Frequent Miler "Best Credit Card Offers": `cards.parse_fm()`
- URL: https://frequentmiler.com/best-credit-card-offers/ (about 1.3 MB of HTML).
- **Table 0 = personal cards (~180 rows), table 1 = business (~55).** Later tables repeat cards by issuer and are ignored.
- Each row: `.BOtmo` → `<strong><a>` card name; the text after it is the offer ("As high as 175K points");
  `.BOfyv` → "ⓘ $2511 1st Yr Value Estimate"; `.FMtipL` → credits breakdown (shown as "Credits:" on the site).
- Links are FM's own `/AmxPlat/#Goto`-style redirects, made absolute.
- **Breaks if** FM renames these CSS classes or reorders tables. Symptom: `fm: 0` in the run log or the Sources table.

### Doctor of Credit "Best Current Credit Card Sign Up Bonuses": `cards.parse_doc()`
- URL: https://www.doctorofcredit.com/best-current-credit-card-sign-bonuses/
- Inside `<article>`, `<h2>` sections: "Personal Cards", "Business Card Bonuses", "YMMV/Targeted Offers" are
  read; "Not On List", "Recent Changes" and "Final Thoughts" stop parsing. Each `<h3>` is a card; the following
  `<p>` siblings up to the next heading are its text.
- Regexes pull out: spend (`spending $4,000`, `after $12,000 spend`, `requires $5,000 in spend`), months or days (days ÷ 30),
  annual fee (`$95 annual fee`, `no annual fee` → 0), first-year waiver, points, cash, and elevated wording.
- Fee and spend are **only known for DoC-listed cards**. FM rows have no spend or fee, so those cells are blank.
- **Breaks if** DoC changes heading levels. Symptom: `doc: 0`.

### Merging FM + DoC: `best_card_offers()`
- Matching is **one-to-one and type-aware**: each DoC card picks its best FM card of the *same* personal/business type
  that isn't already taken, by token Jaccard similarity of 0.5 or more. Tokens drop ®™, numbers, "card", "credit", "business",
  "points", "up to", and so on. (Bug fixed during development: without type-awareness "Venture X Business" matched the personal
  Venture X and created duplicates.)
- DoC picks with no FM match are added on their own with an estimated value.

### Offer value and score
- **Value** = FM's first-year estimate if present. Otherwise points × cents-per-point (`POINT_VALUES` in `cards.py`:
  MR/UR 1.3, TYP/C1 1.2, Bilt 1.4, Hyatt 1.6, Hilton 0.45, Marriott 0.7, airlines 1.0–1.3), plus cash, minus the fee if not waived.
- **Score** = min(70, value/40) +15 DoC pick +10 elevated wording +6 shopping perk (`CLOTHING_PERK` regex: Lululemon,
  Saks, Nordstrom, purchase/return protection, Walmart+, Amazon, Target…) +6 if spend ≤ $4k, −10 if spend ≥ $15k,
  −4 targeted. Then `card_scout.apply_offer_history_signals`: **+10 value up**, **+4 new offer**.
- Business cards dominate on raw value (300K-point offers). The site shows Personal and Business separately, defaulting to Personal.

### Rakuten cash back: `cards.rakuten_rates()`
- `rakuten.com/stores/all` is client-rendered: its HTML holds only footer links, so it **can't be used as a directory**.
  Instead, slugs are guessed from each store name in `config.RAKUTEN_STORES` (`oldnavy`, `jcrew`, `abercrombieandfitch`,
  `j-crew`, first word) and validated by the page `<title>`, which reads
  "*Store* Coupons, Promo Codes & **2% Cash Back** - November 2026 | Rakuten" (or "& No Cash Back", "Up to 15%").
- `fetch_head` reads only until `</title>`, so pages stay cheap. About 100 of 118 stores resolve.
- **Breaks if** Rakuten changes its title format. Symptom: `rakuten: 0`.
- TopCashback (403) and cashbackmonitor.com (connection refused) are blocked for scripts, so Rakuten is the only portal.

### Card news: `card_scout.gather_news()` + `news.py`
- RSS: Doctor of Credit (main, cards, bank bonuses), The Points Guy, One Mile at a Time, Frequent Miler, Upgraded
  Points, Million Mile Secrets, View from the Wing, CreditCards.com, NerdWallet. Plus 10 Slickdeals keyword searches
  (`config.SLICKDEALS_QUERIES`).
- **Relevance:** the title must match `CARD_RELEVANCE` and must not match `CARD_JUNK`. The Slickdeals "credit card" search returns
  RFID wallets, microSD cards and similar, which is why `CARD_JUNK` exists.
- **Category:** the first match in `CARD_CATEGORIES`, in order. *Points, Awards & Transfers is checked first* so "[Award Alert] stays
  from 150K points" isn't read as a sign-up bonus. Award posts are also excluded from the bonus-value read (`AWARD_RE`).
- **Score:** see the docstring in `news.py`. Clothing and department stores in `SHOPPING_RETAILERS` add +10.
- US Credit Card Guide was dropped because its titles are in Chinese.
- **Reddit:** anonymous `.json`/`.rss` requests return 403 or 429 since 2025, so it only works with OAuth app keys.

---

## 4b. Deal Scout reads this site's data (a contract)

Since 2026-11-18, every Deal Scout build fetches `https://pjmerica.github.io/card-scout/cards.json` for its stack-hint badges
(`deal-scout/stacks.py`). Keep these fields stable, or update `stacks.py` in the same change:
- `rakuten[]`: `store`, `rate`, `pct`, `url`, `elevated`
- `news[]`: `title`, `link`, `card_category` ("Shopping & Card-Linked Offers"), `retailers`, `age_days`, `warnings`

If Card Scout is down, Deal Scout just shows no badges and notes it in its health check.

## 4c. Breakage alerts

`tools/health.py` runs as the last CI step, even when earlier steps fail. It keeps one GitHub issue, **"Site health: needs
attention"**: opened when a source falls below its floor (Frequent Miler 150+, Doctor of Credit 40+, Rakuten 70+, news 50+,
80%+ of sources online, Reddit excluded) or a test fails. It updates when the problem list changes and closes itself when the
next build passes. No open issue means nothing to do. The workflow needs `permissions: issues: write`.

## 5. Memory between runs: `history.py`
- At start, in CI, it downloads `https://pjmerica.github.io/card-scout/history.json` (the previous deploy's copy).
  Locally it reads `site/history.json`. Override with the `HISTORY_URL` env var. Nothing is committed.
- `offers`: per card name, a series of values. **Value up** = at least 10% *and* at least $50 above the best value seen before.
  **New offer** = a card name first seen after the baseline run.
- `rakuten`: per slug, a rate series. **Elevated** = above the median of the series. **Highest seen** = its max.
- `news`: first-seen per link (Slickdeals thread id when present). **NEW** = appeared in this run or the previous one.
  The baseline run never marks anything new.
- If the live site is down or the file is missing, the run starts a fresh history (`runs_tracked` resets to 0).
  Signals return after two runs.
- Card names are the keys, so if FM renames a card, it shows up as a "new offer" once.

---

## 6. How to change common things
- **Add a news feed:** append to `config.FEEDS` (`name`, `boost`, `url`). It appears in the Sources table automatically.
- **Add a Rakuten store:** append its display name to `config.RAKUTEN_STORES`. If the slug guess fails, it's silently skipped:
  check `https://www.rakuten.com/shop/<slug>` by hand and extend `slugs()` in `cards.rakuten_rates` if needed.
- **Re-weight ranking:** offers are in `cards.best_card_offers` (the block that builds `score`); news is `config.CARD_HOT_TERMS`,
  `SHOPPING_RETAILER_BONUS`, `NEWS_HALF_LIFE_DAYS`; history bumps are in `card_scout.apply_offer_history_signals`.
- **Point valuations:** `cards.POINT_VALUES` (only used when FM has no estimate), and `config.POINT_VALUE_CENTS` for news titles.
- **Every logic change needs a regression case** in `tests/test_cards.py`. Any new tab or field must render in `tests/smoke.js`.

---

## 7. Known limitations
- Values are estimates. FM's include credits at FM's valuations. Targeted or "as high as" offers vary by person
  (flagged as Targeted, and as variable in the data).
- Spend and fee are blank for cards that aren't on DoC's list.
- Personal targeted offers (Amex Offers / Chase Offers in your own account) are not visible to scrapers (see §8).
- GitHub cron can start runs late, sometimes by hours. Trigger manually with `gh workflow run cards.yml` if needed.
- Node 20 deprecation warnings from `configure-pages`, `upload-pages-artifact` and `deploy-pages` are harmless. Bump them when newer majors exist.

---

## 8. Future work (discussed with the user on 2026-11-18, deferred: "we can do that later")

**Your own Amex/Chase card-linked offers.** The user asked whether logging in to Amex/Chase would let us scrape them. Agreed approach:
- **Never** store bank credentials in GitHub or automate logins in CI: two-factor auth, bot detection, terms of
  service, and the site is public.
- **Option A (preferred first):** the user copies each offers page (Ctrl+A) into a local text file. A parser extracts
  merchant / spend / reward / expiry and cross-references Deal Scout's deals and brand sales plus Rakuten rates into
  "stacks" (for example, a Nordstrom Amex Offer of $20 back on $100 + Rakuten 2% + a 40% sale ≈ 60% off).
- **Option B:** with the Claude in Chrome extension or the Claude desktop app's built-in browser, the user logs in themselves and
  Claude reads the offers pages (read-only; no "Add to card" clicks unless asked).
- **Option C:** CardPointers (third-party app) auto-adds and lists offers.
- **The output must stay private**: a local file or private page, gitignored, never the public Pages site.

Other ideas: TopCashback, Capital One Shopping or airline portal rates if a scrapable source appears; per-card benefit
lookups (purchase/return protection windows); alerts (GitHub issue or email) when a tracked offer goes "Value up".
