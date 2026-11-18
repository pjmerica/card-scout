"""
Card Scout configuration: feeds, classification rules, scoring knobs, store lists, playbook.
Everything tunable lives here; see HANDOFF.md for what each piece feeds into.
"""

# ---------------------------------------------------------------------------
# Scoring knobs
# ---------------------------------------------------------------------------
NEWS_HALF_LIFE_DAYS = 10       # card news score halves every N days of age
MAX_AGE_DAYS = 30              # ignore posts older than this
POINT_VALUE_CENTS = 1.2        # rough value of 1 point/mile when a news title quotes a points bonus
SHOPPING_RETAILER_BONUS = 10   # card-linked offers at clothing/department stores rank higher

# ---------------------------------------------------------------------------
# Card news feeds (RSS/Atom).  boost = flat score bonus for trusted sources
# ---------------------------------------------------------------------------
FEEDS = [
    {"name": "Doctor of Credit", "boost": 6, "url": "https://www.doctorofcredit.com/feed/"},
    {"name": "Doctor of Credit (Cards)", "boost": 6, "url": "https://www.doctorofcredit.com/category/credit-cards/feed/"},
    {"name": "Doctor of Credit (Bank Bonuses)", "boost": 0,
     "url": "https://www.doctorofcredit.com/category/bank-account-bonuses/feed/"},
    {"name": "The Points Guy", "boost": 0, "url": "https://thepointsguy.com/feed/"},
    {"name": "One Mile at a Time", "boost": 0, "url": "https://onemileatatime.com/feed/"},
    {"name": "Frequent Miler", "boost": 2, "url": "https://frequentmiler.com/feed/"},
    {"name": "Upgraded Points", "boost": 0, "url": "https://upgradedpoints.com/feed/"},
    {"name": "Million Mile Secrets", "boost": 0, "url": "https://millionmilesecrets.com/feed/"},
    {"name": "View from the Wing", "boost": 0, "url": "https://viewfromthewing.com/feed/"},
    {"name": "CreditCards.com", "boost": 0, "url": "https://www.creditcards.com/news/feed/"},
    {"name": "NerdWallet", "boost": 0, "url": "https://www.nerdwallet.com/blog/feed/"},
]

# Slickdeals keyword searches for card-linked offers, portals and bonuses (one RSS query each)
SLICKDEALS_QUERIES = [
    "credit card", "amex offer", "chase offer", "capital one offer", "rakuten", "cash back",
    "statement credit", "sign up bonus", "bank bonus", "discover 5%",
]
SLICKDEALS_SEARCH_URL = "https://slickdeals.net/newsearch.php?q={q}&searcharea=deals&searchin=first&rss=1"

# Optional Reddit (needs REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET; anonymous access is blocked)
REDDIT_SUBS = [("CreditCards", 0), ("churning", 2), ("awardtravel", 0)]

# ---------------------------------------------------------------------------
# News classification
# ---------------------------------------------------------------------------
# A post must match one of these in its title to count as card/points news at all
CARD_RELEVANCE = [r"credit card", r"\bcard\b", r"\bamex\b", r"american express", r"\bchase\b", r"\bciti\b",
                  r"capital one", r"discover", r"wells fargo", r"\bbilt\b", r"u\.?s\.? bank", r"barclays",
                  r"bank of america", r"\bpoints\b", r"\bmiles\b", r"cash ?back", r"\bbonus\b", r"\boffers?\b",
                  r"rakuten", r"shopping portal", r"\bportal\b", r"checking", r"savings", r"\bpaypal\b",
                  r"statement credit", r"membership rewards", r"ultimate rewards", r"thankyou", r"venture",
                  r"sapphire", r"freedom", r"platinum", r"gold card", r"apple card", r"robinhood", r"\bsofi\b",
                  r"brokerage", r"gift card", r"\bbank\b"]

# Searches pull in junk that merely contains the word "card"
CARD_JUNK = (r"wallet|card holder|rfid|sd card|microsd|graphics card|memory card|video card|card reader|"
             r"playing card|trading card|pok[eé]mon|card game|greeting card|card table|capture card|sound card|"
             r"network card|giveaway|sweepstakes")

# First matching category wins (order matters: awards before sign-up so "150K points stays" isn't a bonus)
CARD_CATEGORIES = [
    ("Points, Awards & Transfers",
     [r"transfer bonus", r"\(1:\d", r"award", r"buy points", r"buy miles", r"redeem", r"redemption",
      r"one-way", r"round-?trip", r"\bstays?\b", r"\bi fly\b", r"transfer partner"]),
    ("Shopping & Card-Linked Offers",
     [r"amex offers?", r"chase offers?", r"capital one offers?", r"citi merchant", r"bankamerideals",
      r"\boffers?:", r"% back", r"cash ?back", r"rakuten", r"topcashback", r"shopping portal", r"\bportal\b",
      r"gift card", r"black friday", r"cyber monday", r"holiday shopping", r"statement credit", r"5%",
      r"rotating", r"quarterly categor", r"\$\d+ back", r"cardholders", r"card offer", r"spend \$\d+",
      r"price protection", r"purchase protection", r"return protection", r"extended warranty", r"paypal",
      r"amazon", r"walmart", r"target", r"nordstrom", r"macy"]),
    ("Sign-up Bonuses",
     [r"sign-?up bonus", r"welcome (?:bonus|offer)", r"\d{2,3},000", r"\d{2,3}k\b", r"after (?:you )?spend",
      r"elevated", r"all-time high", r"highest (?:ever|offer|bonus)", r"best (?:ever|offer)", r"new offer",
      r"increased bonus", r"targeted"]),
    ("Bank & Brokerage Bonuses",
     [r"checking", r"savings", r"bank bonus", r"brokerage", r"\bcd\b", r"\bhysa\b", r"direct deposit",
      r"money market", r"credit union"]),
]

# Score bonuses for words in a news title/summary
CARD_HOT_TERMS = {
    r"elevated|increased bonus|all-time high|highest (?:ever|offer|bonus)|best (?:ever|offer)|record": 15,
    r"limited[- ]time|ends soon|expires": 5,
    r"no annual fee|\$0 annual fee": 6,
    r"black friday|cyber monday|holiday shopping|gift": 10,
    r"amex offers?|chase offers?|capital one offers?|citi merchant|bankamerideals": 8,
    r"rakuten|topcashback|shopping portal|portal bonus": 8,
    r"5%|rotating|quarterly categor": 7,
    r"price protection|purchase protection|return protection|extended warranty": 6,
}
CARD_DEAD_TERMS = r"\b(?:dead|expired|ended|no longer available|discontinued)\b|\[expired\]|\[dead\]"

# Clothing / department stores: a card-linked offer or portal post naming one gets SHOPPING_RETAILER_BONUS
SHOPPING_RETAILERS = [
    "nordstrom", "nordstrom rack", "macy's", "macys", "kohl's", "kohls", "saks", "saks off 5th", "neiman marcus",
    "bloomingdale's", "jcpenney", "dillard's", "old navy", "gap", "banana republic", "j.crew", "jcrew", "levi's",
    "nike", "adidas", "under armour", "lululemon", "the north face", "patagonia", "columbia", "uniqlo", "h&m",
    "zara", "express", "abercrombie", "american eagle", "ll bean", "l.l.bean", "lands' end", "eddie bauer",
    "rei", "dick's", "foot locker", "finish line", "zappos", "dsw", "new balance", "puma", "ugg", "steve madden",
    "coach", "kate spade", "michael kors", "ralph lauren", "calvin klein", "tommy hilfiger", "brooks brothers",
    "jos. a. bank", "men's wearhouse", "bonobos", "everlane", "madewell", "anthropologie", "free people",
    "urban outfitters", "athleta", "fabletics", "loft", "ann taylor", "carter's", "children's place", "asos",
    "shein", "revolve", "shopbop", "farfetch", "ssense", "allbirds", "hoka", "skechers", "crocs", "vans",
]

# ---------------------------------------------------------------------------
# Rakuten: clothing / department stores to look up (store page slugs are guessed from names
# and validated against the page title, see cards.rakuten_rates)
# ---------------------------------------------------------------------------
RAKUTEN_STORES = [
    "Old Navy", "Gap", "Gap Factory", "Banana Republic", "Banana Republic Factory", "J.Crew", "J.Crew Factory",
    "Levi's", "Nike", "adidas", "Under Armour", "The North Face", "Columbia Sportswear", "Nordstrom",
    "Nordstrom Rack", "Macy's", "Kohl's", "JCPenney", "Saks Fifth Avenue", "Saks OFF 5TH", "Bloomingdale's",
    "Neiman Marcus", "Express", "Abercrombie & Fitch", "Hollister", "American Eagle", "Aerie", "L.L.Bean",
    "Lands' End", "Eddie Bauer", "UNIQLO", "H&M", "ASOS", "Zappos", "DSW", "Famous Footwear", "Foot Locker",
    "Finish Line", "New Balance", "PUMA", "Reebok", "UGG", "Dr. Martens", "Timberland", "Sorel", "Merrell",
    "Crocs", "Skechers", "Converse", "Vans", "HOKA", "REI", "Backcountry", "Dick's Sporting Goods", "Champion",
    "Hanes", "Calvin Klein", "Tommy Hilfiger", "Ralph Lauren", "Brooks Brothers", "Jos. A. Bank",
    "Men's Wearhouse", "Bonobos", "Everlane", "Todd Snyder", "Madewell", "Anthropologie", "Free People",
    "Urban Outfitters", "Athleta", "Fabletics", "LOFT", "Ann Taylor", "Chico's", "Torrid", "Lane Bryant",
    "Carter's", "The Children's Place", "Vineyard Vines", "Lucky Brand", "Guess", "Steve Madden", "Coach Outlet",
    "Kate Spade", "Michael Kors", "Allbirds", "Patagonia", "Lululemon", "Quince", "Nautica", "Perry Ellis",
    "Cole Haan", "Clarks", "Birkenstock", "Saucony", "Brooks Running", "ASICS", "Mango", "Revolve", "Shopbop",
    "Farfetch", "SSENSE", "Mr Porter", "Net-a-Porter", "Taylor Stitch", "Faherty", "Rhone", "Vuori", "Cotopaxi",
    "Duluth Trading", "Carhartt", "Wrangler", "Lee", "Dockers", "Spanx", "SKIMS", "Aritzia", "Zara",
]

# ---------------------------------------------------------------------------
# Card playbook (evergreen guidance shown on the site)
# ---------------------------------------------------------------------------
PLAYBOOK = [
    ("Stack 4 layers on every purchase",
     "Go through a shopping portal (Rakuten, TopCashback, Capital One Shopping, or an airline/hotel portal; "
     "compare rates at cashbackmonitor.com), then add a card-linked offer (Amex Offers, Chase Offers, "
     "Capital One Offers, BankAmeriDeals, Citi Merchant Offers), pay with your best-earning card, and use a "
     "retailer promo code. Clothing retailers often run elevated portal rates over Black Friday weekend."),
    ("Check your card-linked offers before checkout",
     "Open your card apps and add every clothing or department-store offer you see (Nordstrom, Macy's, "
     "Saks, Lands' End, J.Crew and others show up often). Offers are targeted and usually have to be added before "
     "you buy."),
    ("Use Q4 5% rotating categories",
     "Discover it, Chase Freedom Flex and similar cards often put Amazon, Target, Walmart, PayPal or "
     "department stores in their Q4 5% category. Activate it, check this quarter's list, and watch the "
     "per-quarter spending cap."),
    ("Lean on purchase and return protection",
     "Many premium and mid-tier cards cover theft or damage for 90–120 days, and some offer return "
     "protection when a store won't take an item back. That's useful for gifts and final-sale clothing. "
     "Check your card's benefits guide, because these perks have been cut on several cards."),
    ("Time a new card's sign-up bonus to holiday spending",
     "If you were going to spend anyway, opening a card with a strong sign-up bonus before Black Friday "
     "makes the minimum spend easier to hit. Use the Sign-up offers table and prioritize offers marked "
     "elevated or value-up."),
    ("Think twice about store cards",
     "'Save 20% today' store cards usually carry APRs of 30% or more and count as a hard inquiry. They're only "
     "worth it if you pay in full and shop there a lot. A general rewards card plus a portal often beats them."),
    ("Discounted gift cards",
     "Retailers and warehouse clubs often sell gift cards at a discount over Black Friday (for example, "
     "$100 for $80), and card-linked offers sometimes stack on top. Buy gift cards for stores you already "
     "shop, then use them during the sales."),
    ("Pay the full balance",
     "Interest erases any discount. Treat these tips as a way to get more value from spending you already "
     "planned."),
]
