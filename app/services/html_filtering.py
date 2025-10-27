from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup, Tag
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.core.config import (
    CANDIDATE_TAGS,
    CARD_DETAIL_HREF_PATTERNS,
    CARD_HIGHLIGHT_SELECTORS,
    CARD_LOCATION_SELECTORS,
    CARD_MIN_SELECTOR_HITS,
    CARD_PRICE_PATTERN,
    CARD_PRICE_SELECTORS,
    CARD_SELLER_SELECTORS,
    CARD_SHIPPING_SELECTORS,
    CARD_STOP_WORDS,
    CARD_SUBTITLE_SELECTORS,
    CARD_TITLE_SELECTORS,
    DETAIL_HREF_PATTERNS,
    MIN_SIGNATURE_HITS,
    TOP_SIGNATURES,
)
from app.models.cards import Cards
from app.services.llm_engine import get_llm

DEFAULT_REQUIRED_FIELDS: Sequence[str] = ("title", "url")
DEFAULT_MAX_SELECTORS = 6
DEFAULT_CARD_LIMIT = 32


class SelectorScore(BaseModel):
    selector: str = Field(..., description="CSS selector for the candidate wrapper")
    score: int = Field(..., ge=0, le=5, description="Confidence rating (0-5)")
    reason: str = Field(..., description="Rationale for the score")


class SelectorRanking(BaseModel):
    candidates: List[SelectorScore]


@dataclass
class SelectorReport:
    selector: str
    raw_count: int
    sample_cards: List[Cards]


def gather_wrapper_candidates(html: str, base_url: str | None = None) -> tuple[
    List[tuple[tuple[str, Tuple[str, ...]], Tag, bool, bool]],
    Counter[tuple[str, Tuple[str, ...]]],
]:
    soup = BeautifulSoup(html, "lxml")
    counter: Counter[tuple[str, Tuple[str, ...]]] = Counter()
    candidates: List[tuple[tuple[str, Tuple[str, ...]], Tag, bool, bool]] = []

    href_patterns = CARD_DETAIL_HREF_PATTERNS or DETAIL_HREF_PATTERNS

    for node in soup.find_all(CANDIDATE_TAGS):
        classes = tuple(sorted(node.get("class", [])))
        signature = (node.name, classes)

        text = node.get_text(" ", strip=True)
        has_price = bool(CARD_PRICE_PATTERN.search(text))

        has_link = False
        any_anchor = False
        for anchor in node.find_all("a", href=True):
            href = anchor.get("href")
            if not href:
                continue
            any_anchor = True
            normalized = _normalize_url(href, base_url) if base_url else href
            if any(pattern in normalized for pattern in href_patterns):
                has_link = True
                break

        if not has_link and not any_anchor:
            continue
        if not has_link and any_anchor:
            has_link = True

        candidates.append((signature, node, has_price, has_link))
        counter[signature] += 1

    return candidates, counter


def shortlist_signatures(
    candidates: Iterable[tuple[tuple[str, Tuple[str, ...]], Tag, bool, bool]],
    counter: Counter[tuple[str, Tuple[str, ...]]],
    *,
    min_hits: int | None = None,
    top_n: int | None = None,
) -> List[Dict[str, Any]]:
    min_hits = min_hits or min(CARD_MIN_SELECTOR_HITS, MIN_SIGNATURE_HITS)
    top_n = top_n or TOP_SIGNATURES

    grouped: Dict[tuple[str, Tuple[str, ...]], Dict[str, Any]] = {}

    for signature, node, has_price, _ in candidates:
        frequency = counter[signature]
        if frequency < min_hits:
            continue

        entry = grouped.setdefault(
            signature,
            {
                "signature": signature,
                "frequency": frequency,
                "has_price_hits": 0,
                "samples": [],
            },
        )
        if has_price:
            entry["has_price_hits"] += 1
        if len(entry["samples"]) < 3:
            entry["samples"].append(node)

    scored: List[Dict[str, Any]] = []
    for signature, data in grouped.items():
        score = data["frequency"] + data["has_price_hits"]
        data["score"] = score
        first_node = data["samples"][0] if data["samples"] else None
        data["preview_html"] = first_node.prettify() if first_node else ""
        scored.append(data)

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_n]


def signature_to_css(signature: tuple[str, Tuple[str, ...]]) -> str:
    tag, class_tuple = signature
    class_part = "".join(f".{klass}" for klass in class_tuple if klass)
    return f"{tag}{class_part}"


def rank_signatures_with_llm(signature_infos: Sequence[Dict[str, Any]]) -> List[SelectorScore]:
    if not signature_infos:
        return []

    parser = PydanticOutputParser(pydantic_object=SelectorRanking)
    prompt = PromptTemplate.from_template(
        (
            "You are ranking HTML fragments that may be product cards.\n\n"
            "Return JSON with a single key `candidates`, whose value is an array of\n"
            "{\"selector\": string, \"score\": 0-5, \"reason\": string}.\n\n"
            "Fragments:\n{fragments}"
        )
    )

    fragments = "\n\n".join(
        (
            "---\n"
            f"Index: {idx}\n"
            f"Tag/Classes: {info['signature']}\n"
            "HTML snippet:\n"
            f"{info['preview_html'][:1200]}"
        )
        for idx, info in enumerate(signature_infos, start=1)
    )

    llm = get_llm()
    chain = prompt | llm | parser
    try:
        ranking = chain.invoke({"fragments": fragments})
    except Exception:
        return []

    return ranking.candidates


def discover_card_selectors(
    html: str,
    *,
    base_url: str | None = None,
    use_llm: bool = False,
    max_selectors: int = DEFAULT_MAX_SELECTORS,
) -> List[str]:
    candidates, counter = gather_wrapper_candidates(html, base_url=base_url)
    shortlist = shortlist_signatures(candidates, counter)

    selectors = [signature_to_css(item["signature"]) for item in shortlist]
    selectors = selectors[:max_selectors]

    if use_llm and shortlist:
        llm_rankings = rank_signatures_with_llm(shortlist)
        ordered: List[str] = []
        seen: set[str] = set()
        for candidate in llm_rankings:
            selector = candidate.selector.strip()
            if selector and selector in selectors and selector not in seen:
                ordered.append(selector)
                seen.add(selector)
        ordered.extend(sel for sel in selectors if sel not in seen)
        selectors = ordered[:max_selectors]

    return selectors


def extract_cards(
    html: str,
    *,
    base_url: str | None = None,
    limit: int = DEFAULT_CARD_LIMIT,
    use_llm: bool = False,
    required_fields: Iterable[str] | None = None,
    max_selectors: int = DEFAULT_MAX_SELECTORS,
    include_report: bool = False,
) -> List[Cards] | tuple[List[Cards], List[SelectorReport]]:
    selectors = discover_card_selectors(
        html,
        base_url=base_url,
        use_llm=use_llm,
        max_selectors=max_selectors,
    )

    soup = BeautifulSoup(html, "lxml")
    required = tuple(required_fields or DEFAULT_REQUIRED_FIELDS)
    seen: set[str] = set()
    cards: List[Cards] = []
    reports: List[SelectorReport] = []

    for selector in selectors:
        nodes = soup.select(selector)
        if not nodes:
            continue

        selector_cards: List[Cards] = []
        for node in nodes:
            record = _extract_card_from_node(node, base_url=base_url)
            if not _meets_required(record, required):
                continue

            dedupe_key = record.get("url") or record.get("title")
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            card_model = Cards(**record)
            selector_cards.append(card_model)
            cards.append(card_model)

            if len(cards) >= limit:
                break

        reports.append(
            SelectorReport(
                selector=selector,
                raw_count=len(selector_cards),
                sample_cards=selector_cards[: min(len(selector_cards), 5)],
            )
        )

        if len(cards) >= limit:
            break

    return (cards, reports) if include_report else cards


def _extract_card_from_node(node: Tag, base_url: str | None = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    link = _pick_link(node, base_url=base_url)
    if link:
        data["url"] = link

    title = _pick_text(node, CARD_TITLE_SELECTORS)
    if not title:
        title = link[0:80] if link else ""
    data["title"] = title or None
    data["name"] = title or None

    price_text = _pick_text(node, CARD_PRICE_SELECTORS)
    if not price_text:
        price_text = _match_price(node)
    data["price"] = price_text or None

    subtitle = _pick_text(node, CARD_SUBTITLE_SELECTORS)
    data["description"] = subtitle or None

    shipping = _pick_text(node, CARD_SHIPPING_SELECTORS)
    if shipping:
        data.setdefault("specs", {})["shipping"] = shipping

    location = _pick_text(node, CARD_LOCATION_SELECTORS)
    data["location"] = location or None

    seller = _pick_text(node, CARD_SELLER_SELECTORS)
    data["seller"] = seller or None

    highlights = _collect_highlights(node, CARD_HIGHLIGHT_SELECTORS)
    if highlights:
        specs = dict(data.get("specs") or {})
        specs["highlights"] = highlights
        data["specs"] = specs

    image_url = _pick_image(node, base_url=base_url)
    data["image_url"] = image_url or None

    rating, reviews = _pick_rating(node)
    data["rating"] = rating
    data["reviews_count"] = reviews

    return {key: value for key, value in data.items() if value not in (None, "", {})}


def _normalize_url(href: str, base_url: str) -> str:
    from urllib.parse import urljoin as _urljoin

    return _urljoin(base_url, href)


def _pick_link(node: Tag, base_url: str | None = None) -> Optional[str]:
    candidates = node.select("a[href]")
    preferred_patterns = CARD_DETAIL_HREF_PATTERNS or DETAIL_HREF_PATTERNS

    for anchor in candidates:
        href = anchor.get("href")
        if not href:
            continue
        url = _normalize_url(href, base_url) if base_url else href
        if any(pattern in url for pattern in preferred_patterns):
            return url

    for anchor in candidates:
        href = anchor.get("href")
        if href:
            return _normalize_url(href, base_url) if base_url else href
    return None


def _pick_text(node: Tag, selectors: Sequence[str], min_len: int = 4) -> str:
    for selector in selectors:
        element = node.select_one(selector)
        if not element:
            continue
        text = element.get_text(" ", strip=True)
        if len(text) >= min_len and text.lower() not in CARD_STOP_WORDS:
            return text
    return ""


def _match_price(node: Tag) -> str:
    text = node.get_text(" ", strip=True)
    match = CARD_PRICE_PATTERN.search(text or "")
    return match.group(0) if match else ""


def _collect_highlights(node: Tag, selectors: Sequence[str]) -> List[str]:
    results: List[str] = []
    for selector in selectors:
        for element in node.select(selector):
            text = element.get_text(" ", strip=True)
            if text and text.lower() not in CARD_STOP_WORDS:
                results.append(text)
    seen: Dict[str, None] = {}
    for item in results:
        if item not in seen:
            seen[item] = None
    return list(seen.keys())


def _pick_image(node: Tag, base_url: str | None = None) -> Optional[str]:
    image = node.select_one("img[src], img[data-src], img[data-image-src], img[data-lazy-src], img[data-original]")
    if not image:
        return None
    for attr in ("data-src", "data-image-src", "data-original", "srcset", "src"):
        value = image.get(attr)
        if not value:
            continue
        if attr == "srcset":
            value = value.split()[0]
        return _normalize_url(value, base_url) if base_url else value
    return None


def _pick_rating(node: Tag) -> tuple[Optional[float], Optional[int]]:
    rating_value: Optional[float] = None
    reviews_count: Optional[int] = None

    rating_candidate = node.select_one("[aria-label*='out of 5'], [data-star-rating], [class*='rating']")
    if rating_candidate:
        text = rating_candidate.get_text(" ", strip=True)
        parts = text.split()
        for part in parts:
            try:
                rating_value = float(part)
                break
            except ValueError:
                continue

    review_candidate = node.find(string=lambda value: isinstance(value, str) and "review" in value.lower())
    if review_candidate:
        digits = "".join(ch for ch in review_candidate if ch.isdigit() or ch == ",")
        if digits:
            try:
                reviews_count = int(digits.replace(",", ""))
            except ValueError:
                reviews_count = None

    return rating_value, reviews_count


def _meets_required(data: Dict[str, Any], required: Sequence[str]) -> bool:
    for field in required:
        value = data.get(field)
        if value:
            continue
        return False
    return True
