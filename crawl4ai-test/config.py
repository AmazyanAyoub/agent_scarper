# # BASE_URL = "https://www.ebay.com/sch/i.html?_nkw=iphone+15&_sacat=0&_from=R40&_trksid=p4432023.m570.l1312"
# # CSS_SELECTOR = "[class^='su-card-container']"
# # REQUIRED_KEYS = ["title", "url", "price"]

# # config.py
# BASE_URL = "https://www.ebay.com/sch/i.html?_nkw=iphone+15&_ipg=120"  # many items, no scrolling

# # Tell the scraper to auto-pick from candidates
# CSS_SELECTOR = "AUTO"

# # Order matters: your eBay class first, then general fallbacks
# CANDIDATE_SELECTORS = [
#     "[class^='su-card-container']",          # your find
#     "ul.srp-results > li.s-item",            # eBay default
#     "[data-component-type='s-search-result']", # Amazon
#     "div.product-card, article.product-card",
#     "[class*='card']:not([class*='grid'])",
#     "[class*='result']:not([class*='grid'])",
#     "article:has(a[href])"
# ]

# # keep small batches to avoid huge prompts
# MAX_CARDS_PER_PAGE = 16
# # we accept a selector when it yields at least this many items
# MIN_GOOD_HITS = 6

# # stay lenient
# REQUIRED_KEYS = ["title", "url"]


# config.py
BASE_URL = "https://www.ebay.com/sch/i.html?_nkw=iphone+15&_ipg=120"   # server renders many

# Ask the scraper to auto-pick a card selector
CSS_SELECTOR = "AUTO"

# Try these in order; add your finds here (yours first)
CANDIDATE_SELECTORS = [
    "[class^='su-card-container']",          # your eBay variant
    "ul.srp-results > li.s-item",            # eBay classic
    "[data-component-type='s-search-result']",  # Amazon
    "div.product-card, article.product-card",
    "[class*='card']:not([class*='grid'])",
    "[class*='result']:not([class*='grid'])",
    "article:has(a[href])"
]

# Auto-detection thresholds
MIN_GOOD_HITS = 6           # accept a selector when it yields at least this many cards
MAX_CARDS_PER_PAGE = 24     # cap how many we parse/store per page

# Keep deterministic parsing lenient
REQUIRED_KEYS = ["title", "url"]

