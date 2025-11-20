from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.core.logger import get_logger
from app.services.chains.builders import build_search_intent_chain
from app.services.chains.models import SearchIntentSchema

logger = get_logger(__name__)

_search_intent_chain = None  # ← add this
def _get_search_intent_chain():
    global _search_intent_chain
    if _search_intent_chain is None:
        _search_intent_chain = build_search_intent_chain()
    return _search_intent_chain


@dataclass
class SearchCondition:
    name: str
    value: str
    # apply_via: str

@dataclass
class SearchIntent:
    keyword: str
    conditions: List[SearchCondition]


def build_search_intent(instruction: str) -> SearchIntent:
    chain = _get_search_intent_chain()
    clean_instruction = instruction.strip()

    logger.info("Requesting search intent from LLM")
    try:
        intent: SearchIntentSchema = chain.invoke({"instruction": clean_instruction})
        keyword = intent.keyword or "udgu"
        conditions = [SearchCondition(name=c.name, value=c.value) for c in intent.conditions]
        return intent
    except Exception as exc:
        logger.error("Search intent parsing failed: %s", exc)
        return SearchIntent(keyword="udgu", conditions=[clean_instruction])
    

def build_search_keyword(instruction: str) -> str:
    keyword_parts: list[str] = []
    search_intent = build_search_intent(instruction)

    if search_intent.keyword and search_intent.keyword.lower() != "udgu":
        keyword_parts.append(search_intent.keyword.strip())
    else:
        logger.warning("No keyword found in instruction")

    for condition in search_intent.conditions:
        if isinstance(condition, str):
            keyword_parts.append(condition.strip())
            continue
        # if condition.apply_via == "keyword" and condition.value:
        if condition.value:
            keyword_parts.append(condition.value.strip())

    return " ".join(part for part in keyword_parts if part)


