# parser.py

import json
import re
from dataclasses import dataclass
from typing import List

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger

from app.core.config import SEARCH_ATTRS, SEARCH_TERMS
from app.prompts.prompts import SEARCH_SELECTORS_PROMPT
from app.services.llm_engine import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


@dataclass
class SelectorCandidate:
    """Internal structure used to merge ranked selector guesses."""
    css: str
    confidence: int
    source: str


def _attr_tokens(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v]
    return [str(value)]


def clean_json_text(text: str) -> str:
    """Remove markdown fences like ```json ... ``` if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    return text


def detect_search_selectors(html: str, limit: int = 10) -> List[str]:
    """
    Return up to `limit` CSS selectors, ranked by confidence, merged from
    heuristic and LLM sources.
    """
    candidates: List[SelectorCandidate] = []
    candidates.extend(_detect_search_selectors_heuristic(html, limit))
    candidates.extend(_detect_search_selectors_llm(html, limit))

    ordered = sorted(candidates, key=lambda c: c.confidence, reverse=True)
    seen: set[str] = set()
    result: List[str] = []

    for cand in ordered:
        if cand.css in seen:
            continue
        seen.add(cand.css)
        result.append(cand.css)
        if len(result) >= limit:
            break

    logger.info("Search selector candidates: %s", result)
    return result


def _detect_search_selectors_heuristic(html: str, limit: int) -> List[SelectorCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[SelectorCandidate] = []

    inputs = soup.find_all("input", attrs={"type": re.compile("search|text", re.I)})
    for tag in inputs:
        attrs = " ".join(
            " ".join(_attr_tokens(tag.get(attr)))
            for attr in SEARCH_ATTRS
        )
        score = 3
        if re.search(SEARCH_TERMS, attrs, re.I):
            score += 2
        css = build_selector(tag)
        results.append(
            SelectorCandidate(
                css=css,
                confidence=min(score, 5),
                source="heuristic",
            )
        )
        if len(results) >= limit:
            break

    return results


def _detect_search_selectors_llm(html: str, limit: int) -> List[SelectorCandidate]:
    snippet = html[:8000]
    prompt = PromptTemplate.from_template(SEARCH_SELECTORS_PROMPT)
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    try:
        payload_raw = chain.invoke({"snippet": snippet})
        payload = json.loads(clean_json_text(payload_raw))
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON selector payload.")
        return []

    selectors: List[SelectorCandidate] = []
    for item in payload.get("selectors", [])[:limit]:
        css = (item.get("css") or "").strip()
        if not css:
            continue
        selectors.append(
            SelectorCandidate(
                css=css,
                confidence=int(item.get("confidence", 3)),
                source="llm"
            )
        )
    return selectors


def build_selector(tag: Tag) -> str:
    tag_id = tag.get("id")
    if tag_id:
        return f"input#{tag_id}"

    classes = [cls for cls in _attr_tokens(tag.get("class")) if cls]
    if classes:
        return "input." + ".".join(classes[:3])

    for attr in ("name", "placeholder", "aria-label"):
        value = tag.get(attr)
        if value:
            return f"input[{attr}='{value}']"

    return "input"
