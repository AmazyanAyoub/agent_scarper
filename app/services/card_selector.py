# app/services/card_selector.py

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag

from app.models.cards import Cards
from app.services.chains.builders import build_card_mapping_chain
from app.services.chains.models import CardMapping, CardMappingResult
from app.core.config import PRICE_REGEX, MIN_SIBLINGS, MAX_NODES, TOP_K, IMAGE_ATTRS

from langchain_core.exceptions import OutputParserException

from app.core.logger import get_logger
logger = get_logger(__name__)

@dataclass
class CardSelectorCandidate:
    selector: str
    count: int
    avg_score: float
    sample_html: str


@dataclass
class CardExtractionResult:
    cards: List[Cards]
    selector: Optional[str]
    mapping: Optional[CardMapping]


def _class_key(node: Tag) -> Tuple[str, ...]:
    classes = node.get("class") or []
    return tuple(sorted({cls.strip() for cls in classes if cls and cls.strip()}))


def is_price_like(s: str) -> bool:
    s = s.strip()
    digits = re.sub(r"\D", "", s)
    has_currency = bool(re.search(r'[€$£¥₺₹]|USD|EUR|GBP|JPY|INR|MAD|DH', s, re.I))
    return (len(digits) >= 3) or has_currency

def _extract_image_url(el):
    img = el.find("img")
    if not img:
        return None
    for attr in ("data-src", "data-image-src", "data-original", "data-lazy-src", "srcset", "src"):
        value = img.get(attr)
        if not value:
            continue
        if attr == "srcset":
            value = value.split()[0]
        value = value.strip()
        if value:
            return value
    return None


def _score(node: Tag) -> int:
    score = 0
    if node.find("img"):
        score += 3
    if node.find("a", href=True):
        score += 2
    text = node.get_text(" ", strip=True) or ""
    if PRICE_REGEX.search(text):
        score += 4
    words = len(text.split())
    if 3 <= words <= 80:
        score += 1
    return score
# def _score(el):
#     s = 0
#     text = el.get_text(" ", strip=True) or ""
#     words = len(text.split())

#     # --- 1. Image quality ---
#     imgs = el.find_all("img")
#     if imgs:
#         s += 2
#         # small boost if non-placeholder
#         src = imgs[0].get("data-src") or imgs[0].get("src") or ""
#         if src and not src.startswith("data:image"): 
#             s += 1

#     # --- 2. Link presence ---
#     if el.find("a", href=True):
#         s += 2

#     # --- 3. Price check ---
#     price_found = False
#     for m in PRICE_REGEX.finditer(text):
#         if is_price_like(m.group(0)):
#             s += 3
#             price_found = True
#             break
#     if not price_found:
#         s -= 1  # slight penalty

#     # --- 4. Title / text quality ---
#     if 3 <= words <= 50:
#         s += 2
#     elif words > 0:
#         s += 1

#     # --- 5. Text-to-image ratio (too little text = ad/banner) ---
#     ratio = words / max(1, len(imgs))
#     if 0.3 <= ratio <= 100:  # reasonable range
#         s += 1

#     # --- 6. Penalize repetitive / ad classes ---
#     bad_tokens = ["carousel", "banner", "ad", "promo", "snap", "sponsor", "track"]
#     classes = " ".join(el.get("class") or []).lower()
#     if any(b in classes for b in bad_tokens):
#         s -= 3
#     return s


def discover_card_selectors(
    html: str,
    *,
    min_siblings: int = MIN_SIBLINGS,
    top_k: int = TOP_K,
) -> List[CardSelectorCandidate]:
    soup = BeautifulSoup(html, "lxml")
    buckets: Dict[Tuple[int, Tuple[str, ...]], List[Tag]] = defaultdict(list)

    for node in soup.select("[class]"):
        parent = node.parent
        if not isinstance(parent, Tag):
            continue
        key = _class_key(node)
        if not key:
            continue
        buckets[(id(parent), key)].append(node)

    candidates: List[CardSelectorCandidate] = []
    for (_, key), nodes in buckets.items():
        if len(nodes) < min_siblings:
            continue

        sample_nodes = nodes[: min(6, len(nodes))]
        avg_score = sum(_score(n) for n in sample_nodes) / len(sample_nodes)

        selector = f"{nodes[0].name or 'div'}{''.join(f'.{token}' for token in key)}"
        match_count = len(soup.select(selector))
        if match_count < min_siblings or match_count > 5000:
            continue

        snippet = sample_nodes[0].prettify() if sample_nodes else ""
        candidates.append(
            CardSelectorCandidate(
                selector=selector,
                count=match_count,
                avg_score=avg_score,
                sample_html=snippet,
            )
        )

    candidates.sort(key=lambda c: (c.avg_score, c.count), reverse=True)
    return candidates[:top_k]

def infer_field_mapping(card_html: str) -> CardMapping:
    chain = build_card_mapping_chain()
    try:
        result = chain.invoke({"card_html": card_html})
    except OutputParserException as err:
        logger.error("Card mapping parser failure: %s", err)
        return _fallback_card_mapping(card_html)

    if isinstance(result, CardMappingResult) and result.candidates:
        return result.candidates[0]

    try:
        return CardMapping(**(result.get("candidates", [{}])[0]))
    except Exception:
        return _fallback_card_mapping(card_html)


def _first(node: Tag, selectors: Optional[str]) -> Optional[Tag]:
    if not selectors:
        return None
    for part in (s.strip() for s in selectors.split(",") if s.strip()):
        match = node.select_one(part)
        if match:
            return match
    return None
def _fallback_card_mapping(card_html: str) -> CardMapping:
    soup = BeautifulSoup(card_html, "lxml")
    title = soup.select_one("h1, h2, h3, a")
    price = soup.select_one("[class*='price'], span")
    image = soup.select_one("img")
    link = soup.select_one("a[href]")
    return CardMapping(
        title=title.name if title else None,
        price="[class*='price'], span" if price else None,
        image="img" if image else None,
        link="a[href]" if link else None,
    )

def extract_cards_with_mapping(
    html: str,
    selector: str,
    mapping: CardMapping,
    *,
    base_url: str | None = None,
    limit: int = MAX_NODES,
) -> List[Cards]:
    soup = BeautifulSoup(html, "lxml")
    cards: List[Cards] = []
    seen: set[str] = set()

    for node in soup.select(selector)[:limit]:
        title_el = _first(node, mapping.title)
        price_el = _first(node, mapping.price)
        image_el = _first(node, mapping.image)
        link_el = _first(node, mapping.link)

        title = title_el.get_text(" ", strip=True) if title_el else None
        price = price_el.get_text(" ", strip=True) if price_el else None

        image_url = None
        if image_el:
            image_url = (
                image_el.get("data-src")
                or image_el.get("src")
                or (
                    image_el.get("srcset", "").split()[0]
                    if image_el.has_attr("srcset")
                    else None
                )
            )
            if image_url:
                image_url = image_url.strip()

        if not image_url:
            image_url = _extract_image_url(node)

        if image_url and base_url:
            image_url = urljoin(base_url, image_url)

        link_url = None
        if link_el and link_el.has_attr("href"):
            href = link_el["href"]
            if base_url:
                link_url = urljoin(base_url, href)
            else:
                link_url = href

        dedupe_key = link_url or title
        if dedupe_key and dedupe_key in seen:
            continue
        if dedupe_key:
            seen.add(dedupe_key)

        cards.append(
            Cards(
                title=title,
                price=price,
                image_url=image_url,
                url=link_url,
            )
        )

    return cards

def extract_cards_from_html(
    html: str,
    *,
    base_url: str | None = None,
    top_k: int = TOP_K,
    limit: int = MAX_NODES,
    cached_selector: str | None = None,
    cached_mapping: dict | None = None,
    reuse_cached: bool = True,
) -> CardExtractionResult:
    if reuse_cached and cached_selector:
        mapping_obj: CardMapping | None = None
        if cached_mapping:
            try:
                mapping_obj = CardMapping(**cached_mapping)
            except Exception:
                mapping_obj = None
        if mapping_obj:
            cards = extract_cards_with_mapping(
                html,
                cached_selector,
                mapping_obj,
                base_url=base_url,
                limit=limit,
            )
            return CardExtractionResult(
                cards=cards,
                selector=cached_selector,
                mapping=mapping_obj,
            )

    candidates = discover_card_selectors(html, top_k=top_k)
    if not candidates:
        return CardExtractionResult(cards=[], selector=None, mapping=None)

    best = candidates[0]
    mapping = infer_field_mapping(best.sample_html)
    cards = extract_cards_with_mapping(
        html,
        best.selector,
        mapping,
        base_url=base_url,
        limit=limit,
    )
    return CardExtractionResult(cards=cards, selector=best.selector, mapping=mapping)
