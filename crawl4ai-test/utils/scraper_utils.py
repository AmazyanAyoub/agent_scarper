# # utils/scraper_utils.py
# import json
# import os
# from pathlib import Path
# from typing import List, Set, Tuple, Dict

# from crawl4ai import (
#     AsyncWebCrawler,
#     BrowserConfig,
#     CacheMode,
#     CrawlerRunConfig,
#     LLMExtractionStrategy,
#     LLMConfig
# )
# from dotenv import load_dotenv

# from models.Cards import Card   # Venue remains alias of Card for compatibility
# from utils.data_utils import is_complete_venue, is_duplicate_venue
# from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
# from config import CANDIDATE_SELECTORS, MAX_CARDS_PER_PAGE, MIN_GOOD_HITS

# load_dotenv()


# def _limit_selector(sel: str, n: int) -> str:
#     # keep only the first n nodes to bound tokens
#     return f"{sel}:nth-child(-n+{n})" if ":nth-child(" not in sel else sel



# async def _auto_pick_selector(
#     crawler, url: str, session_id: str, llm_strategy, required_keys
# ) -> str | None:
#     # Try each candidate; return the first that extracts >= MIN_GOOD_HITS items
#     for sel in CANDIDATE_SELECTORS:
#         limited = _limit_selector(sel, MAX_CARDS_PER_PAGE)
#         result = await crawler.arun(
#             url=url,
#             config=CrawlerRunConfig(
#                 cache_mode=CacheMode.BYPASS,
#                 session_id=session_id,
#                 wait_until="domcontentloaded",
#                 wait_for=sel,                       # wait for this candidate to exist
#                 wait_for_timeout=45000,
#                 css_selector=limited,               # only a small batch
#                 extraction_strategy=llm_strategy,
#                 simulate_user=True,
#                 remove_overlay_elements=True,
#                 magic=True,
#                 # keep prompts small by default (no full page)
#                 # log_console=True, screenshot=True,  # enable if you want debug
#             ),
#         )
#         if not (result.success and result.extracted_content):
#             continue
#         items = json.loads(result.extracted_content) or []
#         # apply the same minimal completeness filter
#         good = [it for it in items if is_complete_venue(it, required_keys)]
#         if len(good) >= MIN_GOOD_HITS:
#             print(f"[AUTO] Using selector: {sel}  (got {len(good)} items)")
#             return sel
#     print("[AUTO] No selector produced enough items; falling back to first candidate.")
#     return CANDIDATE_SELECTORS[0] if CANDIDATE_SELECTORS else None


# def get_browser_config() -> BrowserConfig:
#     return BrowserConfig(
#         browser_type="chromium",
#         enable_stealth=True,
#         headless=False,                    # headful reduces blocks while testing
#         use_persistent_context=True,       # keep cookies/session
#         user_data_dir=str(Path(__file__).parent / ".user-data"),
#         viewport_width=1366,
#         viewport_height=768,
#         ignore_https_errors=True,
#         extra_args=["--disable-blink-features=AutomationControlled"],
#         headers={
#             "Accept-Language": "en-US,en;q=0.9",
#             "Referer": "https://www.google.com/",
#             "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                            "AppleWebKit/537.36 (KHTML, like Gecko) "
#                            "Chrome/118.0.0.0 Safari/537.36"),
#         },
#         verbose=True,
#     )

# def get_llm_strategy() -> LLMExtractionStrategy:
#     llm_config = LLMConfig(
#         provider="groq/llama-3.1-8b-instant",
#         api_token=os.getenv("GROQ_API_KEY"),
#         temperature=0.0,
#     )
#     instruction = (
#         "Extract listing cards ONLY from the selected nodes. "
#         "Use ONLY attributes inside those nodes (no guessing). "
#         "title: visible title text. "
#         "url: prefer the main item link within the card (e.g., <a class='s-item__link'>, "
#         "or any href that looks like a product detail), do not fabricate. "
#         "image_url: main <img> src or data-src. "
#         "price: copy exactly as shown. "
#         "Return a strict JSON array matching the schema."
#     )
#     return LLMExtractionStrategy(
#         llm_config=llm_config,
#         schema=Card.model_json_schema(),
#         extraction_type="schema",
#         instruction=instruction,
#         input_format="html",   # IMPORTANT for href/src
#         verbose=True,
#     )

# def _normalize_key(item: Dict) -> str:
#     url = (item.get("url") or item.get("link") or item.get("href") or "").strip()
#     if url:
#         return url
#     title = (item.get("title") or item.get("name") or "").strip()
#     price = (item.get("price") or "").strip()
#     return f"{title}|{price}" if title else ""

# def _with_page(base_url: str, page_number: int) -> str:
#     u = urlparse(base_url); q = dict(parse_qsl(u.query))
#     if "ebay." in u.netloc:
#         q["_pgn"] = str(page_number)      # <-- correct pager for eBay
#         q.pop("page", None)
#     else:
#         q["page"] = str(page_number)
#     return urlunparse(u._replace(query=urlencode(q)))

# async def fetch_and_process_page(
#     crawler: AsyncWebCrawler,
#     page_number: int,
#     base_url: str,
#     css_selector: str,
#     llm_strategy: LLMExtractionStrategy,
#     session_id: str,
#     required_keys: List[str],
#     seen_names: Set[str],
# ) -> Tuple[List[dict], bool]:
#     url = _with_page(base_url, page_number)
#     print(f"Loading page {page_number}...")

#     # Decide the selector
#     if css_selector == "AUTO":
#         sel = await _auto_pick_selector(
#             crawler, url=url, session_id=session_id, llm_strategy=llm_strategy, required_keys=required_keys
#         )
#         if not sel:
#             print("No usable selector detected.")
#             return [], False
#     else:
#         sel = css_selector

#     # Now do one final extraction with the chosen selector (bounded)
#     limited_sel = _limit_selector(sel, MAX_CARDS_PER_PAGE)

#     result = await crawler.arun(
#         url=url,
#         config=CrawlerRunConfig(
#             cache_mode=CacheMode.BYPASS,
#             session_id=session_id,
#             wait_until="networkidle",
#             wait_for="ul.srp-results, li.s-item",
#             wait_for_timeout=10000,
#             extraction_strategy=None,          # ← no LLM involved
#             simulate_user=True,
#             remove_overlay_elements=True,
#             magic=True,
#             scan_full_page=True,
#             scroll_delay=0.2,
#             mean_delay=0.5,
#             max_range=1.2,
#             js_code=[
#                 "(()=>{document.querySelector('#gdpr-banner-accept,button#gdpr-banner-accept,button[aria-label*\"Accept\"]').click?.()})()",
#                 "(()=>{const sel=['button[aria-label=\"Accept All\"]','button[aria-label=\"Accept\"]','button[aria-label=\"Close\"]']; for(const s of sel){const b=document.querySelector(s); if(b){b.click();break;}}})()",
#             ],
#             log_console=True,
#             screenshot=True,
#         ),
#     )

#     debug_dir = Path("debug")
#     debug_dir.mkdir(exist_ok=True)
#     (debug_dir / f"page_{page_number}_raw.html").write_text(result.html or "", encoding="utf-8")


#     if not (result.success and result.extracted_content):
#         # Helpful debug: show a bit of the markdown if nothing extracted
#         md = getattr(result, "markdown", "")
#         print(f"Error fetching page {page_number}: {result.error_message}")
#         print(f"DEBUG markdown({len(md)} chars): {md[:500].replace(os.linesep,' ')}")
#         return [], False

#     extracted_data = json.loads(result.extracted_content) or []
#     if not extracted_data:
#         print(f"No cards found on page {page_number}.")
#         md = getattr(result, "markdown", "")
#         print(f"DEBUG markdown({len(md)} chars): {md[:500].replace(os.linesep,' ')}")
#         return [], False

#     print("Extracted data:", extracted_data)

#     real = []
#     for item in extracted_data:
#         if item.get("error") is False:
#             item.pop("error", None)

#         # Only accept real item pages — NOT category/collection/search
#         url = (item.get("url") or "").strip()
#         if not url or "/itm/" not in url:
#             continue

#         if not is_complete_venue(item, required_keys):
#             continue

#         # stronger dedupe: title + url
#         key = (item.get("title") or item.get("name") or "").strip() + "|" + url
#         if is_duplicate_venue(key, seen_names):
#             continue

#         seen_names.add(key)
#         real.append(item)

#     if not real:
#         print(f"No complete cards found on page {page_number}.")
#         return [], False

#     print(f"Extracted {len(real)} cards from page {page_number}.")
#     return real, False

# utils/scraper_utils.py
import asyncio, json, os, re
from typing import List, Set, Tuple, Dict, Optional
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from dotenv import load_dotenv

from config import CANDIDATE_SELECTORS, MIN_GOOD_HITS, MAX_CARDS_PER_PAGE
from utils.data_utils import is_complete_venue, is_duplicate_venue

load_dotenv()

ITEM_URL_RE = re.compile(r"/itm/\d+", re.I)   # “real product” on eBay; leave off for general sites if you want

def get_browser_config() -> BrowserConfig:
    return BrowserConfig(
        browser_type="chromium",
        headless=False,
        enable_stealth=True,
        use_persistent_context=True,
        user_data_dir=os.path.join(os.path.dirname(__file__), ".user-data"),
        viewport_width=1366, viewport_height=768,
        headers={"Accept-Language": "en-US,en;q=0.9"},
        verbose=True,
    )

def _with_page(base_url: str, page_number: int) -> str:
    u = urlparse(base_url); q = dict(parse_qsl(u.query))
    if "ebay." in u.netloc:  # correct pager for eBay; keeps _ipg if present
        q["_pgn"] = str(page_number); q.pop("page", None)
    else:
        q["page"] = str(page_number)
    return urlunparse(u._replace(query=urlencode(q)))

def _abs(url: str, base: str) -> str:
    try:
        return urljoin(base, url)
    except Exception:
        return url

def _cap(sel: str, n: int) -> str:
    # Cap volume passed to parser (not required but keeps it fast)
    return f"{sel}:nth-child(-n+{n})" if ":nth-child(" not in sel else sel

def _auto_pick_selector(soup: BeautifulSoup) -> Optional[str]:
    # 1) try candidate list in order
    for sel in CANDIDATE_SELECTORS:
        nodes = soup.select(sel)
        if len(nodes) >= MIN_GOOD_HITS:
            return sel
    # 2) fallback heuristic: find a repeated element that contains links/images/prices
    best_sel, best_count = None, 0
    for tag in ("li", "div", "article", "section"):
        for el in soup.find_all(tag, limit=2000):
            # must have at least one link and some text; prices/images get a bonus
            has_link = el.select_one("a[href]")
            if not has_link: continue
            txt = el.get_text(" ", strip=True)
            has_price = bool(re.search(r"[$€£]\s?\d", txt))
            has_img = bool(el.select_one("img[src], img[data-src]"))
            score = (1 + has_price + has_img)
            if score >= 2:
                # build a simple selector from first class (generic but effective)
                classes = (el.get("class") or [])
                if classes:
                    candidate = f"{tag}.{classes[0]}"
                else:
                    candidate = tag
                cnt = len(soup.select(candidate))
                if cnt > best_count:
                    best_count, best_sel = cnt, candidate
    return best_sel

def _extract_cards_from_nodes(nodes, page_url: str) -> List[Dict]:
    items = []
    for node in nodes:
        # URL – prefer product/detail links; fallback to first <a>
        a = (node.select_one("a.s-item__link[href]") or
             node.select_one("a[href*='/itm/']") or
             node.select_one("a[href]"))
        url = _abs(a["href"], page_url) if a else None

        # Title – common title holders
        t = (node.select_one(".s-item__title") or
             node.select_one("h3, h2, h4, .title, [aria-label]"))
        title = (t.get_text(" ", strip=True) if t else (a.get_text(" ", strip=True) if a else None))

        # Image
        img = node.select_one("img[src], img[data-src], img[data-image-src]")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src") or img.get("data-image-src")
            image_url = _abs(image_url, page_url)

        # Price (quick heuristic)
        price_el = (node.select_one(".s-item__price") or node.select_one(".price"))
        price = price_el.get_text(" ", strip=True) if price_el else None
        if not price:
            m = re.search(r"([$€£]\s?\d[\d,\.]*)", node.get_text(" ", strip=True))
            price = m.group(1) if m else None

        # Rating / reviews (best-effort)
        rating = None
        rr = node.select_one("[aria-label*='out of 5']")
        if rr:
            m = re.search(r"(\d+(?:\.\d+)?)\s*out of\s*5", rr.get("aria-label",""))
            if m: rating = float(m.group(1))

        reviews_count = None
        rc = node.find(string=re.compile(r"(rating|review)s?", re.I))
        if rc:
            m = re.search(r"(\d[\d,]*)", rc)
            if m: reviews_count = int(m.group(1).replace(",", ""))

        items.append({
            "title": title or None,
            "url": url or None,
            "image_url": image_url or None,
            "price": price or None,
            "rating": rating,
            "reviews_count": reviews_count,
        })
    return items

async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,                # we accept this but “AUTO” means detect            # kept for signature compatibility, unused
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    url = _with_page(base_url, page_number)
    print(f"Loading page {page_number}...")

    # 1) fetch rendered HTML (no LLM at all)
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
            wait_until="networkidle",
            wait_for="ul, ol, section, main, [class*='result'], [class*='card']",
            wait_for_timeout=10000,
            simulate_user=True,
            remove_overlay_elements=True,
            magic=True,
            scan_full_page=True,
            scroll_delay=0.2,
            # scan_full_page left off; _ipg=120 already renders many
        ),
    )
    if not result.success:
        print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    html = result.html or ""
    soup = BeautifulSoup(html, "html.parser")

    # 2) pick the card selector
    if css_selector == "AUTO":
        sel = _auto_pick_selector(soup)
        if not sel:
            print("No card selector detected.")
            return [], False
        print(f"[AUTO] Using selector: {sel}")
    else:
        sel = css_selector

    # 3) select & cap nodes, then parse deterministically
    nodes = soup.select(_cap(sel, MAX_CARDS_PER_PAGE))
    if not nodes:
        print(f"No nodes matched selector: {sel}")
        return [], False

    raw_items = _extract_cards_from_nodes(nodes, page_url=url)

    # 4) clean/filter/dedupe (keep only real product-ish URLs for eBay)
    out = []
    for it in raw_items:
        if not is_complete_venue(it, required_keys):
            continue
        if "ebay." in urlparse(url).netloc and it.get("url") and not ITEM_URL_RE.search(it["url"]):
            continue
        key = (it.get("url") or it.get("title") or "").strip()
        if not key or is_duplicate_venue(key, seen_names):
            continue
        seen_names.add(key)
        out.append(it)

    if not out:
        print(f"No complete cards found on page {page_number}.")
        return [], False

    print(f"Extracted {len(out)} cards from page {page_number}.")
    return out, False
