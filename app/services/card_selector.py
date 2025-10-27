# app/services/card_selector.py

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup, Tag
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.models.cards import Cards
from app.services.llm_engine import get_llm

from app.core.config import PRICE_REGEX, MIN_SIBLINGS, MAX_NODES, TOP_K


@dataclass
class CardSelectorCandidate:
    selector: str
    count: int
    avg_score: float
    sample_html: str


class CardMapping(BaseModel):
    title: str | None = Field(None, description="Relative selector(s) for title")
    price: str | None = Field(None, description="Relative selector(s) for price")
    image: str | None = Field(None, description="Relative selector(s) for image")
    link: str | None = Field(None, description="Relative selector(s) for link")


class CardMappingResult(BaseModel):
    candidates: List[CardMapping]


@dataclass
class CardExtractionResult:
    cards: List[Cards]
    selector: Optional[str]
    mapping: Optional[CardMapping]


def _class_key(node: Tag) -> Tuple[str, ...]:
    classes = node.get("class") or []
    return tuple(sorted({cls.strip() for cls in classes if cls and cls.strip()}))


def _score(node: Tag) -> float:
    score = 0.0
    if node.find("img"):
        score += 3
    if node.find("a", href=True):
        score += 2
    if PRICE_REGEX.search(node.get_text(" ", strip=True) or ""):
        score += 4
    token_count = len((node.get_text(" ", strip=True) or "").split())
    if 3 <= token_count <= 80:
        score += 1
    return score


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


def _mapping_chain():
    parser = PydanticOutputParser(pydantic_object=CardMappingResult)
    prompt = PromptTemplate.from_template(
        "You are an expert HTML analyzer for e-commerce product cards. "
        "Given a product-card snippet, output JSON with CSS selectors (relative to that snippet) "
        "for title, price, image, link. Use comma-separated selectors if needed; set null when missing. "
        '{{"candidates":[{{"title": "...", "price": "...", "image": "...", "link": "..."}}]}} '
        "HTML SNIPPET: {card_html}"
    )
    return prompt | get_llm() | parser


def infer_field_mapping(card_html: str) -> CardMapping:
    chain = _mapping_chain()
    result = chain.invoke({"card_html": card_html})

    if isinstance(result, CardMappingResult) and result.candidates:
        return result.candidates[0]

    try:
        return CardMapping(**(result.get("candidates", [{}])[0]))
    except Exception:
        return CardMapping()  # fall back to nulls


def _first(node: Tag, selectors: Optional[str]) -> Optional[Tag]:
    if not selectors:
        return None
    for part in (s.strip() for s in selectors.split(",") if s.strip()):
        match = node.select_one(part)
        if match:
            return match
    return None


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
            src = image_el.get("data-src") or image_el.get("src")
            if src and base_url:
                from urllib.parse import urljoin
                image_url = urljoin(base_url, src)
            else:
                image_url = src

        link_url = None
        if link_el and link_el.has_attr("href"):
            href = link_el["href"]
            if base_url:
                from urllib.parse import urljoin
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
) -> CardExtractionResult:
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