# config.py

from dotenv import load_dotenv
import os, re
from loguru import logger
from pathlib import Path
# Load .env file
load_dotenv()

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

MAX_DEPTH = 5


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