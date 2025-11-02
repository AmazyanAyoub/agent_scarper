# config.py

from dotenv import load_dotenv
import os, re
from pathlib import Path
from typing import Tuple
# Load .env file
load_dotenv()

from app.core.logger import get_logger
logger = get_logger(__name__)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DATA_FILE = "app/data/classified_sites.json"

DEFAULT_SELECTOR_CACHE_PATH = Path("app/data/selector_cache.json")

SUSPECT_TEXT_KEYWORDS = (
    "unusual traffic",
    "are you a robot",
    "verification required",
    "enable javascript",
    "checking your browser",
    "check your browser before accessing",
    "please wait while we",
    "security check",
)

SUSPECT_SELECTORS = (
    "#cf-wrapper",
    "#cmsg",
    "#captcha",
    ".g-recaptcha",
    "script[src*='cf/challenge']",
)
# Project Settings
# DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MODEL = "llama-3.3-70b-versatile" 

DEFAULT_PROVIDER = "groq"

# Debug check
if not GROQ_API_KEY:
    logger.warning("⚠️ GROQ_API_KEY not found in .env")

OUTPUT_DIR = "outputs"

# MAX_DEPTH = 5


SEARCH_TERMS = r"(search|query|keyword|product|term|lookup|find)"
SEARCH_ATTRS = ["id", "name", "placeholder", "aria-label", "aria-labelledby",
                "data-testid", "data-test", "class"]

CAPTCHA_SIGNATURES = (
    "baxia-punish",                 # AliExpress slider wall
    "detected unusual traffic",     # generic copy on many captcha pages
    "id=\"nocaptcha\"",             # Ali/Tencent nocaptcha widget
    "cf-challenge",                 # Cloudflare turnstile/hcaptcha
    "recaptcha/api.js",             # Google reCAPTCHA loader
)


PROXY_SERVER = os.getenv("PLAYWRIGHT_PROXY_SERVER", "").strip()
PROXY_USERNAME = os.getenv("PLAYWRIGHT_PROXY_USERNAME", "").strip()
PROXY_PASSWORD = os.getenv("PLAYWRIGHT_PROXY_PASSWORD", "").strip()

PLAYWRIGHT_PROXY = None
if PROXY_SERVER:
    PLAYWRIGHT_PROXY = {"server": PROXY_SERVER}
    if PROXY_USERNAME:
        PLAYWRIGHT_PROXY["username"] = PROXY_USERNAME
    if PROXY_PASSWORD:
        PLAYWRIGHT_PROXY["password"] = PROXY_PASSWORD


BROWSER_ARGS = [
    "--disable-save-password-bubble",
    "--disable-blink-features=AutomationControlled",
    "--disable-web-security",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
    "--no-first-run",
    "--no-default-browser-check",
]

SUSPECT_TITLE_PATTERNS = (
    re.compile(r"cf[- ]?error", re.I),
    re.compile(r"verification required", re.I),
    re.compile(r"attention required", re.I),
)

VIEWPORT={"width": 1280, "height": 720}

USER_AGENT=(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.5993.88 Safari/537.36"
)


MIN_SIBLINGS = 3
TOP_K = 3
MAX_NODES = 50


PRICE_REGEX = re.compile(r"(?:([€$£¥]|USD|EUR|GBP|¥|DH)\s*)?([0-9]+(?:[.,][0-9]{2})?)(?:\s*([€$£¥]|USD|EUR|GBP|¥|DH))?")

IMAGE_ATTRS = (
    "data-src",
    "data-image-src",
    "data-original",
    "data-lazy-src",
    "data-srcset",
    "data-testid",
    "srcset",
    "src",
)

# PRODUCT_CARD_KEYWORDS = (
#     "price",
#     "product",
#     "card",
#     "item",
#     "result",
# )


# PRODUCT_CONTAINER_TAGS: Tuple[str, ...] = ("article", "section", "div[class*='product']", "li[class*='item']", "div[data-product-id']")

# CLASS_KEYWORDS = (
#     "product",
#     "item",
#     "tile",
#     "card",
#     "listing",
#     "offer",
#     "result",
#     "grid",
#     "row",
# )


# ---- Card extraction heuristics ----

# CARD_PRICE_PATTERN = re.compile(
#     r"(?i)([\$€£]\s?)?\d[\d,]*(\.\d{2})?(?:\s?(usd|eur|gbp|dh|aed|sar))?"
# )

# CARD_STOP_WORDS = {
#     "watchlist",
#     "save this search",
#     "sponsored",
#     "shop store",
#     "filter",
#     "add to cart",
# }

# CARD_TITLE_SELECTORS = [
#     '[class*="title"]',
#     '[data-test*="title"]',
#     'h1',
#     'h2',
#     'h3',
#     'h4',
#     'a[href]'
# ]

# CARD_PRICE_SELECTORS = [
#     '[class*="price"]',
#     '[data-test*="price"]',
#     '[data-testid*="price"]',
#     '[class*="amount"]',
#     'span'
# ]

# CARD_SUBTITLE_SELECTORS = [
#     '[class*="subtitle"]',
#     '[data-test*="subtitle"]',
#     '[class*="secondary"]',
#     '[data-testid*="condition"]'
# ]

# CARD_SHIPPING_SELECTORS = [
#     '[class*="shipping"]',
#     '[data-test*="shipping"]',
#     '[data-testid*="shipping"]'
# ]

# CARD_LOCATION_SELECTORS = [
#     '[class*="location"]',
#     '[data-test*="location"]',
#     '[data-testid*="location"]'
# ]

# CARD_SELLER_SELECTORS = [
#     '[class*="seller"]',
#     '[data-test*="seller"]',
#     '[class*="feedback"]'
# ]

# CARD_HIGHLIGHT_SELECTORS = [
#     '[class*="badge"]',
#     '[data-testid*="highlight"]',
#     'ul li'
# ]

# CARD_MIN_SELECTOR_HITS = 6


# CARD_DETAIL_HREF_PATTERNS = (
#     "/itm/",           # eBay
#     "/dp/",            # Amazon
#     "/product/",       # Shopify / others
#     "/listing/",       # Etsy / common
#     "sku=",            # generic SKU links
#     "item="
# )


# DETAIL_HREF_PATTERNS = (
#     "/itm/", "/dp/", "/product/", "/listing/", "sku=", "item="
# )


# CANDIDATE_TAGS = {"article", "li", "div", "section"}

# MIN_SIGNATURE_HITS = 6
# TOP_SIGNATURES = 6