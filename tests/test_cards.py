"""Regression tests for Card Scout's logic. Run: python tests/test_cards.py"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cards  # noqa: E402
import history  # noqa: E402
import news  # noqa: E402
from models import NOW, Item  # noqa: E402


def item(title, summary="", **kw):
    it = Item(title=title, link="https://x.com/" + title[:12].replace(" ", "-"), source=kw.pop("source", "T"),
              summary=summary, **kw)
    it.sources = [it.source]
    news.score(it)
    return it


def test_junk_and_relevance():
    assert not news.relevant(Item(title="RFID Wallet with 12-Card Capacity $9", link="x", source="s"))
    assert not news.relevant(Item(title="Samsung 256GB microSD card $15", link="x", source="s"))
    assert news.relevant(Item(title="Chase Offers: 10% back at Nordstrom", link="x", source="s"))


def test_award_posts_are_not_bonuses():
    it = item("[Award Alert] Waldorf Astoria New York: Book Stays From 150K Points")
    assert it.bonus_value is None and it.card_category == "Points, Awards & Transfers"


def test_signup_bonus_value_and_category():
    it = item("Chase Ink Business Preferred Card Bonus: 100K Points Welcome Offer")
    assert it.bonus_value == 1200 and it.card_category == "Sign-up Bonuses"


def test_card_linked_offer_at_clothing_store_ranks_higher():
    a = item("Amex Offers: Spend $100 at Nordstrom, get $20 back")
    b = item("Amex Offers: Spend $100 at Jiffy Lube, get $20 back")
    assert a.score > b.score and a.card_category == "Shopping & Card-Linked Offers" and "Nordstrom" in a.retailers


def test_american_express_is_not_the_store_express():
    it = item("Amex Offers: NJ Transit $8 off $40 (works at EWR)")
    assert not it.retailers and not any("department store" in r for r in it.reasons)


def test_reasons_are_readable_labels():
    it = item("Capital One Shopping/Offers: Up To 18.5% Back On Giftcards.com")
    assert "Shopping portal deal" in it.reasons and "5% / rotating category" not in it.reasons
    alliant = item("Alliant Credit Union $200 Checking Bonus", "Earn via Rakuten too")
    assert "Shopping portal deal" not in alliant.reasons  # summary mentions don't count for title-only terms


def test_doc_only_offer_text():
    d = {"name": "Chase Southwest 80,000 – 90,000 Points",
         "text": "Read our review Earn 80,000 points after $1,000 spend in 3 months. Another option is 90,000."}
    assert cards._doc_offer(d) == "Earn 80,000 points after $1,000 spend in 3 months."


def test_redemption_word_alone_is_not_awards():
    gas = item("[Extended 1/15/27] OnePay: $1 Cashback Per Gallon Of Gas Every Wednesday (50 Gallons, Two Redemptions Per Day)")
    assert gas.card_category == "Shopping & Card-Linked Offers"
    assert item("How Are Hotels Paid When You Redeem Points, And For Elite Perks?").card_category == "Points, Awards & Transfers"


def test_dead_posts_penalized():
    assert item("[Dead] Citi 75K offer").score < item("Citi 75K offer").score


def test_name_matching_is_one_to_one_and_typed():
    fm = [{"name": "Capital One Venture X Business Card", "business": True},
          {"name": "Capital One Venture X Rewards Credit Card", "business": False}]
    d = {"name": "Capital One Venture X Business Up To 300,000 Points", "business": True}
    assert cards._match(d["name"], fm, True, set()) is fm[0]
    assert cards._match(d["name"], fm, True, {id(fm[0])}) is None


def test_offer_history_value_up_and_new():
    h = {"offers": {}, "rakuten": {}, "news": {}, "runs": []}
    o = [{"name": "Card A", "value": 1000, "offer": "60K"}]
    history.apply_offers(h, o)
    assert not o[0]["new_offer"]  # baseline run
    h["runs"].append((NOW - datetime.timedelta(hours=4)).isoformat())
    o2 = [{"name": "Card A", "value": 1300, "offer": "80K"}, {"name": "Card B", "value": 500, "offer": "$500"}]
    history.apply_offers(h, o2)
    assert o2[0]["value_up"] and o2[0]["prev_best"] == 1000 and o2[1]["new_offer"]


def test_rakuten_elevated():
    h = {"offers": {}, "rakuten": {"macys": {"rates": [["2026-11-01T00:00:00+00:00", 2.0], ["2026-11-02T00:00:00+00:00", 2.0]]}},
         "news": {}, "runs": ["x"]}
    r = [{"slug": "macys", "pct": 10.0}]
    history.apply_rakuten(h, r)
    assert r[0]["elevated"] and r[0]["usual"] == 2.0 and r[0]["max_seen"] == 10.0


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    sys.exit(1 if fails else 0)
