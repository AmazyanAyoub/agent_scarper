# tests/detect_cards.py
from pathlib import Path
from collections import Counter
import json
import re
from typing import Iterable, Optional, List, Dict, Any

from bs4 import BeautifulSoup, Tag

RAW_HTML_PATH = Path("debug/cards_raw.html")
OUTPUT_PATH = Path("debug/cards_enriched.json")

PRICE_PATTERN = re.compile(r"(?i)([\$\u20ac\u00a3]\s?)?\d[\d,]*(\.\d{2})?(?:\s?(usd|eur|gbp|dh))?")
STOP_WORDS = {"watchlist", "save this search", "sponsored", "shop store", "filter"}

TITLE_SELECTORS = [
    '[class*="title"]',
    '[data-test*="title"]',
    "h1",
    "h2",
    "h3",
    "h4",
    'a[href]'
]

PRICE_SELECTORS = [
    '[class*="price"]',
    '[data-test*="price"]',
    '[data-testid*="price"]',
    '[class*="amount"]',
    "span"
]

SUBTITLE_SELECTORS = [
    '[class*="subtitle"]',
    '[data-test*="subtitle"]',
    '[class*="secondary"]',
    '[data-testid*="condition"]'
]

SHIPPING_SELECTORS = [
    '[class*="shipping"]',
    '[data-test*="shipping"]',
    '[data-testid*="shipping"]'
]

LOCATION_SELECTORS = [
    '[class*="location"]',
    '[data-test*="location"]',
    '[data-testid*="location"]'
]

SELLER_SELECTORS = [
    '[class*="seller"]',
    '[data-test*="seller"]',
    '[class*="feedback"]'
]

HIGHLIGHT_SELECTORS = [
    '[class*="badge"]',
    'ul li',
    '[data-testid*="highlight"]'
]


def node_has_price(node: Tag) -> bool:
    text = node.get_text(" ", strip=True).lower()
    if any(stop in text for stop in STOP_WORDS):
        return False
    return bool(PRICE_PATTERN.search(text))


def node_has_anchor(node: Tag) -> bool:
    return any(a.get("href") for a in node.find_all("a", href=True))


def css_path(node: Tag) -> str:
    parts: list[str] = []
    cur: Optional[Tag] = node
    while cur and cur.name not in ("html", "body"):
        classes = "." + ".".join(sorted(c for c in cur.get("class", []) if c))
        parts.append(f"{cur.name}{classes}" if classes != "." else cur.name)
        cur = cur.parent if isinstance(cur.parent, Tag) else None
    return " > ".join(reversed(parts))


def discover_card_selector(html: str, min_hits: int = 6) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = [
        node for node in soup.find_all(["li", "article", "div", "section"])
        if node_has_price(node) and node_has_anchor(node)
    ]
    freq = Counter(css_path(node) for node in candidates)
    for path, hits in freq.most_common():
        if hits < min_hits:
            continue
        try:
            nodes = soup.select(path)
        except Exception:
            continue
        if nodes and node_has_price(nodes[0]) and node_has_anchor(nodes[0]):
            return path
    return None


def _pick_text(node: Tag, selectors: Iterable[str], min_len: int = 4) -> str:
    for sel in selectors:
        for el in node.select(sel):
            text = el.get_text(" ", strip=True)
            if len(text) >= min_len and not any(stop in text.lower() for stop in STOP_WORDS):
                return text
    return ""


def _pick_url(node: Tag, title: str) -> str:
    title_lower = title.lower()
    # Prefer /itm/ links whose text looks like the title we just extracted
    for a in node.select("a[href*='/itm/']"):
        link_text = a.get_text(" ", strip=True).lower()
        if title_lower and title_lower[:20] in link_text:
            return a["href"].strip()
    # Fallback: first /itm/ link
    for a in node.select("a[href*='/itm/']"):
        href = a["href"].strip()
        if href and not href.startswith("javascript:"):
            return href
    # Absolute last resort
    for a in node.find_all("a", href=True):
        href = a["href"].strip()
        if href and not href.startswith("javascript:"):
            return href
    return ""

def _pick_image(node: Tag) -> str:
    img = node.find("img")
    if not img:
        return ""
    for key in ("data-src", "data-image-src", "srcset", "src"):
        val = img.get(key)
        if val:
            # srcset -> take first URL
            if key == "srcset":
                return val.split()[0]
            return val
    return ""


def _collect_highlights(node: Tag, selectors: Iterable[str]) -> List[str]:
    highlights: List[str] = []
    for sel in selectors:
        for el in node.select(sel):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 3 and text.lower() not in STOP_WORDS:
                highlights.append(text)
    return list(dict.fromkeys(highlights))  # de-duplicate preserving order


def parse_price_value(text: str) -> Optional[float]:
    match = PRICE_PATTERN.search(text or "")
    if not match:
        return None
    numeric_part = re.sub(r"[^\d.]", "", match.group(0))
    try:
        return float(numeric_part) if numeric_part else None
    except ValueError:
        return None


def extract_cards_from_html(html: str, limit: int = 50) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    selector = discover_card_selector(html)
    if not selector:
        raise RuntimeError("No product-like selector discovered.")

    cards: List[Dict[str, Any]] = []
    for node in soup.select(selector):
        # text_blob = node.get_text(" ", strip=True).lower().replace(" ", "")
        # if "sponsored" in text_blob or "derosnops" in text_blob:
        #     continue  
    
        title = _pick_text(node, TITLE_SELECTORS, min_len=6)
        url = _pick_url(node, title)
        if not title or not url or "/sch/" in url.lower() or "store" in title.lower():
            continue

        price_text = _pick_text(node, PRICE_SELECTORS, min_len=2)
        price_value = parse_price_value(price_text)
        subtitle = _pick_text(node, SUBTITLE_SELECTORS, min_len=4)
        shipping = _pick_text(node, SHIPPING_SELECTORS, min_len=4)
        location = _pick_text(node, LOCATION_SELECTORS, min_len=4)
        seller = _pick_text(node, SELLER_SELECTORS, min_len=4)
        highlights = _collect_highlights(node, HIGHLIGHT_SELECTORS)
        image_url = _pick_image(node)

        metadata: Dict[str, Any] = {
            "raw_html": node.prettify(),
        }

        if subtitle:
            metadata["subtitle"] = subtitle
        if shipping:
            metadata["shipping"] = shipping
        if location:
            metadata["location"] = location
        if seller:
            metadata["seller"] = seller
        if highlights:
            metadata["highlights"] = highlights

        cards.append(
            {
                "selector": selector,
                "title": title,
                "url": url,
                "price_text": price_text,
                "price_value": price_value,
                "image_url": image_url,
                "metadata": metadata,
            }
        )

        if len(cards) >= limit:
            break

    return cards


def main() -> None:
    html = RAW_HTML_PATH.read_text(encoding="utf-8")
    cards = extract_cards_from_html(html, limit=10)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(cards)} enriched cards to {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()