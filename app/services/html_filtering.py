"""Heuristic product-card extractor for rendered search-result HTML."""

from __future__ import annotations

from collections import Counter
import re
from typing import Iterable, List, Optional

from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from app.models.cards import Cards
from app.core.config import (
    CARD_PRICE_PATTERN,
    CARD_STOP_WORDS,
    CARD_TITLE_SELECTORS,
    CARD_PRICE_SELECTORS,
    CARD_SUBTITLE_SELECTORS,
    CARD_SHIPPING_SELECTORS,
    CARD_LOCATION_SELECTORS,
    CARD_SELLER_SELECTORS,
    CARD_HIGHLIGHT_SELECTORS,
    CARD_MIN_SELECTOR_HITS,
    CARD_DETAIL_HREF_PATTERNS,
)


def _node_has_price(node: Tag) -> bool:
    text = node.get_text(" ", strip=True).lower()
    if any(stop in text for stop in CARD_STOP_WORDS):
        return False
    return bool(CARD_PRICE_PATTERN.search(text))


def _node_has_anchor(node: Tag) -> bool:
    for a in node.find_all("a", href=True):
        href = a["href"]
        if any(pat in href for pat in CARD_DETAIL_HREF_PATTERNS):
            return True
    return False


def _css_path(node: Tag) -> str:
    parts: list[str] = []
    cur: Optional[Tag] = node
    while cur and cur.name not in ("html", "body"):
        classes = "." + ".".join(sorted(c for c in cur.get("class", []) if c))
        parts.append(f"{cur.name}{classes}" if classes != "." else cur.name)
        cur = cur.parent if isinstance(cur.parent, Tag) else None
    return " > ".join(reversed(parts))


def _discover_card_selector(html: str, min_hits: int = 6) -> Optional[str]:
    min_hits = max(min_hits, CARD_MIN_SELECTOR_HITS)
    soup = BeautifulSoup(html, "lxml")
    candidates = [
        node
        for node in soup.find_all(["li", "article", "div", "section"])
        if _node_has_price(node) and _node_has_anchor(node)
    ]
    freq = Counter(_css_path(node) for node in candidates)
    for path, hits in freq.most_common():
        if hits < min_hits:
            continue
        try:
            nodes = soup.select(path)
        except Exception:
            continue
        if nodes and _node_has_price(nodes[0]) and _node_has_anchor(nodes[0]):
            return path
    return None


def _pick_text(node: Tag, selectors: Iterable[str], min_len: int = 4) -> str:
    for sel in selectors:
        for el in node.select(sel):
            text = el.get_text(" ", strip=True)
            if len(text) >= min_len and not any(stop in text.lower() for stop in CARD_STOP_WORDS):
                return text
    return ""


def _pick_url(node: Tag, title: str) -> str:
    title_lower = title.lower()
    for a in node.select("a[href*='/itm/']"):
        href = a["href"].strip()
        link_text = a.get_text(" ", strip=True).lower()
        if href and not href.startswith("javascript:") and title_lower[:32] in link_text:
            return href
    for a in node.select("a[href*='/itm/']"):
        href = a["href"].strip()
        if href and not href.startswith("javascript:"):
            return href
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
            if key == "srcset":
                return val.split()[0]
            return val
    return ""


def _collect_highlights(node: Tag, selectors: Iterable[str]) -> list[str]:
    highlights: list[str] = []
    for sel in selectors:
        for el in node.select(sel):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 3 and text.lower() not in CARD_STOP_WORDS:
                highlights.append(text)
    return list(dict.fromkeys(highlights))


def _parse_price_value(text: str) -> Optional[float]:
    match = CARD_PRICE_PATTERN.search(text or "")
    if not match:
        return None
    numeric_part = re.sub(r"[^\d.]", "", match.group(0))
    try:
        return float(numeric_part) if numeric_part else None
    except ValueError:
        return None


def extract_cards(html: str, limit: int = 50) -> list[Cards]:
    soup = BeautifulSoup(html, "lxml")
    selector = _discover_card_selector(html)
    print(f"[extract_cards] selector -> {selector}")
    if not selector:
        return []

    cards: list[Cards] = []
    for node in soup.select(selector):
        title = _pick_text(node, CARD_TITLE_SELECTORS, min_len=6)
        url = _pick_url(node, title)
        if not title or not url or "/sch/" in url.lower():
            continue

        # text_blob = node.get_text(" ", strip=True).lower().replace(" ", "")
        # if "sponsored" in text_blob or "derosnops" in text_blob:
        #     continue

        price_text = _pick_text(node, CARD_PRICE_SELECTORS, min_len=2)
        price_value = _parse_price_value(price_text)
        subtitle = _pick_text(node, CARD_SUBTITLE_SELECTORS, min_len=4)
        shipping = _pick_text(node, CARD_SHIPPING_SELECTORS, min_len=4)
        location = _pick_text(node, CARD_LOCATION_SELECTORS, min_len=4)
        seller = _pick_text(node, CARD_SELLER_SELECTORS, min_len=4)
        highlights = _collect_highlights(node, CARD_HIGHLIGHT_SELECTORS)
        image_url = _pick_image(node)

        specs = {
            "raw_html": node.prettify(),
            "shipping": shipping,
            "highlights": highlights,
        }
        if subtitle:
            specs["subtitle"] = subtitle
        if location:
            specs["location"] = location
        if seller:
            specs["seller"] = seller

        payload = {
            "title": title,
            "name": title,
            "url": url,
            "image_url": image_url,
            "description": subtitle or "",
            "price": price_text,
            "specs": specs,
            "rating": None,
            "reviews_count": None,
            "availability": None,
            "brand": None,
            "model": None,
            "category": None,
        }

        try:
            card = Cards(**payload)
            cards.append(card)
        except ValidationError:
            continue

        if len(cards) >= limit:
            break

    return cards
