# parser.py

import json
import re
from dataclasses import dataclass
from typing import List

from bs4 import BeautifulSoup
from bs4.element import Tag
from app.core.logger import get_logger
logger = get_logger(__name__)


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


INPUT_TYPE_RE = re.compile(r"search|text", re.I)
SEARCH_TERMS_RE = SEARCH_TERMS if hasattr(SEARCH_TERMS, "search") else re.compile(SEARCH_TERMS, re.I)
SNIPPET_LIMIT = 8000

_PROMPT = PromptTemplate.from_template(SEARCH_SELECTORS_PROMPT)
_STR_PARSER = StrOutputParser()
_CHAIN = None
def _get_selector_chain():
    global _CHAIN
    if _CHAIN is None:
        _CHAIN = _PROMPT | get_llm() | _STR_PARSER
    return _CHAIN

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

    inputs = soup.find_all("input", attrs={"type": INPUT_TYPE_RE})
    for tag in inputs:
        score = 3
        if any(
            SEARCH_TERMS_RE.search(tok)
            for a in SEARCH_ATTRS
            for tok in _attr_tokens(tag.get(a))
        ):
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
    snippet = html[:SNIPPET_LIMIT]
    chain = _get_selector_chain()
    payload_raw = chain.invoke({"snippet": snippet})

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
