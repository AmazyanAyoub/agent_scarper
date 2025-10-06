"""Post-search HTML processing: extract and clean product entries."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from loguru import logger
from app.core.config import PRICE_REGEX, PRODUCT_CONTAINER_TAGS, CLASS_KEYWORDS
from app.services.llm_engine import get_llm   # <-- you said you have this


@dataclass
class ProductEntry:
    title: str
    url: str
    price: Optional[float] = None
    currency: Optional[str] = None
    image: Optional[str] = None
    snippet: Optional[str] = None


USE_LLM_VALIDATION = False 


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def extract_products(html: str, base_url: str, limit: Optional[int] = None) -> List[ProductEntry]:
    """Return a normalized list of product entries from the search results."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Try structured data first
    products = _extract_from_structured_data(soup, base_url)
    if products:
        logger.info("Extracted %d products from structured data", len(products))
        if limit:
            products = products[:limit]
        return products

    # 2. Heuristic DOM scan
    scored_cards = _rank_candidate_cards(soup)
    results: List[ProductEntry] = []
    seen = set()

    for node, _ in scored_cards:
        full_text = node.get_text(" ", strip=True)
        confidence = _compute_confidence(node, full_text)
        entry = _parse_card(node, base_url)
        if not entry:
            continue
        if confidence >= 8:        # ✅ High confidence → accept directly
            pass
        elif confidence >= 4:      # 🤔 Medium → send to LLM
            if USE_LLM_VALIDATION and not _validate_with_llm(entry, node):
                continue
        else:                      # ❌ Low confidence → skip
            continue

        dedupe_key = (entry.title.strip().lower(), entry.url)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        results.append(entry)

        if limit and len(results) >= limit:
            break

    logger.info("Extracted %d product entries", len(results))
    return results


def save_products(products: List[ProductEntry], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(product) for product in products]
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d products to %s", len(products), target)


# ---------------------------------------------------------------------
# Structured Data
# ---------------------------------------------------------------------

def _extract_from_structured_data(soup: BeautifulSoup, base_url: str) -> List[ProductEntry]:
    """Look for JSON-LD / microdata / OpenGraph product info."""
    products: List[ProductEntry] = []

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        if isinstance(data, dict):
            data = [data]
        for item in data:
            if not isinstance(item, dict):
                continue
            if item.get("@type") in ["Product", "Offer"]:
                name = item.get("name") or item.get("title")
                url = urljoin(base_url, item.get("url") or "")
                price = None
                currency = None
                offers = item.get("offers")
                if isinstance(offers, dict):
                    price = offers.get("price")
                    currency = offers.get("priceCurrency")
                elif isinstance(offers, list) and offers:
                    price = offers[0].get("price")
                    currency = offers[0].get("priceCurrency")
                image = item.get("image")
                if name and url:
                    try:
                        price = float(str(price).replace(",", "")) if price else None
                    except:
                        price = None
                    products.append(ProductEntry(title=name, url=url, price=price, currency=currency, image=image))
    return products


# ---------------------------------------------------------------------
# DOM Heuristic Scoring
# ---------------------------------------------------------------------

def _rank_candidate_cards(soup: BeautifulSoup, max_candidates: int = 250) -> List[Tuple[Tag, float]]:
    scored: List[Tuple[Tag, float]] = []
    seen: set[int] = set()

    for price_node in soup.find_all(string=PRICE_REGEX):
        if _looks_like_rating(price_node):
            continue
        container = _bubble_up_to_container(price_node.parent)
        if not container:
            continue
        ident = id(container)
        if ident in seen:
            continue
        seen.add(ident)
        scored.append((container, _score_node(container)))

    if not scored:
        for node in soup.find_all(PRODUCT_CONTAINER_TAGS):
            if not isinstance(node, Tag):
                continue
            if any(keyword in " ".join(node.get("class", [])).lower() for keyword in CLASS_KEYWORDS):
                ident = id(node)
                if ident in seen:
                    continue
                seen.add(ident)
                scored.append((node, _score_node(node)))

    if not scored:
        for node in soup.find_all("a", href=True):
            ident = id(node)
            if ident in seen:
                continue
            seen.add(ident)
            scored.append((node, _score_node(node)))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:max_candidates]


def _bubble_up_to_container(node: Tag | None) -> Optional[Tag]:
    while node and node.name not in PRODUCT_CONTAINER_TAGS:
        node = node.parent  # type: ignore[assignment]
    return node

def _compute_confidence(node: Tag, text: str) -> float:
    score = 0.0
    valid_price = bool(PRICE_REGEX.search(text)) and not _looks_like_rating(text)
    if valid_price:
        score += 5
    if re.search(r'[\$\€\£\¥]|usd|eur|gbp|jpy', text, re.I):
        score += 2
    if node.find("img", src=True):
        score += 2
    anchors = node.find_all("a", href=True)
    if any(len(a.get_text(" ", strip=True).split()) >= 5 for a in anchors):
        score += 2
    classes = " ".join(node.get("class", [])).lower()
    if any(k in classes for k in ["product", "item", "card", "listing"]):
        score += 1
    # repetition: siblings with same tag/class
    sibs = node.find_parent().find_all(node.name, class_=node.get("class")) if node.parent else []
    if sibs and len(sibs) >= 3:
        score += 3
    if _looks_like_rating(text):
        score -= 5
    if valid_price and PRICE_REGEX.search(text) and float(PRICE_REGEX.search(text).group(2).replace(",","") or 0) < 5:
        score -= 3
    if len(text) < 20 or len(text) > 600:
        score -= 2
    return score

def _score_node(node: Tag) -> float:
    text = node.get_text(" ", strip=True)
    score = 0.0

    price_matches = PRICE_REGEX.findall(text)
    if price_matches:
        score += 5 + len(price_matches)

    anchors = node.find_all("a", href=True)
    if anchors:
        score += 4
        if len(anchors) > 1:
            score += 1

    if node.find("img", src=True):
        score += 2

    classes = " ".join(node.get("class", [])).lower()
    for keyword in CLASS_KEYWORDS:
        if keyword in classes:
            score += 1.5
            break

    if 40 <= len(text) <= 600:
        score += 1.5

    depth = 0
    parent = node.parent
    while parent and depth < 6:
        depth += 1
        parent = parent.parent
    score -= depth * 0.3

    if _looks_like_rating(text):
        score -= 6

    return score


def _looks_like_rating(text: str) -> bool:
    return bool(re.search(r"\b\d+(\.\d+)?\s*out\s*of\s*5\s*stars?", text, re.I))


def _parse_card(node: Tag, base_url: str) -> Optional[ProductEntry]:
    full_text = node.get_text(" ", strip=True)
    price_match = PRICE_REGEX.search(full_text)
    if not price_match or _looks_like_rating(full_text):
        return None

    currency = price_match.group(1) or price_match.group(3)
    raw_price = price_match.group(2).replace(",", "")
    try:
        price_value = float(raw_price)
    except ValueError:
        price_value = None

    if price_value is not None and price_value < 5:
        return None

    link = _select_anchor(node)
    if not link:
        return None

    title = link.get_text(" ", strip=True)
    if len(title) < 3:
        return None

    url = urljoin(base_url, link["href"])
    img_tag = node.find("img", src=True)
    image = urljoin(base_url, img_tag["src"]) if img_tag else None
    snippet = _extract_snippet(node, exclude=link)

    return ProductEntry(title=title, url=url, price=price_value, currency=currency, image=image, snippet=snippet)


def _select_anchor(node: Tag) -> Optional[Tag]:
    anchors = node.find_all("a", href=True)
    if not anchors:
        return None
    def anchor_score(a: Tag) -> float:
        score = len(a.get_text(" ", strip=True))
        if a.find("img"):
            score += 5
        return score
    anchors.sort(key=anchor_score, reverse=True)
    return anchors[0]


def _extract_snippet(node: Tag, exclude: Tag) -> Optional[str]:
    for desc_tag in node.find_all(["p", "span", "div"]):
        if desc_tag is exclude:
            continue
        text = desc_tag.get_text(" ", strip=True)
        if 20 <= len(text) <= 200:
            return text
    return None


# ---------------------------------------------------------------------
# Optional LLM Validation
# ---------------------------------------------------------------------

def _validate_with_llm(entry: ProductEntry, node: Tag) -> bool:
    """Ask LLM if this looks like a valid product card."""
    try:
        llm = get_llm()
    except Exception:
        return True  # if no LLM available, skip validation

    prompt = (
        "You are an HTML product card validator.\n"
        "Given the following HTML snippet, decide if it is a real product (not a review widget or rating):\n\n"
        f"Title: {entry.title}\nPrice: {entry.price} {entry.currency}\n"
        f"Snippet: {entry.snippet}\nHTML:\n{str(node)[:1500]}\n\n"
        "Answer with only 'yes' or 'no'."
    )
    try:
        result = llm.invoke(prompt)
        if isinstance(result, str):
            text = result.lower()
        else:
            text = str(result).lower()
        return "yes" in text
    except Exception:
        return True  # fail open
