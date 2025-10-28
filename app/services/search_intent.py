from dataclasses import dataclass
from typing import List, Literal
from loguru import logger
from pydantic import BaseModel, Field
from app.prompts.prompts import SEARCH_INTENT_PROMPT
from app.services.llm_engine import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


class SearchConditionModel(BaseModel):
    name: str = Field(..., description="Machine-friendly condition name, e.g. price_max, brand")
    value: str = Field(..., description="Human-readable value to apply")
    apply_via: Literal["keyword", "filter"] = Field(
        ...,
        description="Whether to append to the search keyword or apply via UI filters",
    )

class SearchIntentSchema(BaseModel):
    keyword: str = Field(default="udgu")
    conditions: List[SearchConditionModel] = Field(default_factory=list)


@dataclass
class SearchCondition:
    name: str
    value: str
    apply_via: str

@dataclass
class SearchIntent:
    keyword: str
    conditions: List[SearchCondition]


def build_search_intent(instruction: str) -> SearchIntent:
    prompt = PromptTemplate.from_template(SEARCH_INTENT_PROMPT)
    llm = get_llm()
    parser = PydanticOutputParser(pydantic_object=SearchIntentSchema)
    chain = prompt | llm | parser

    logger.info("Requesting search intent from LLM")
    try:
        intent: SearchIntent = chain.invoke({"instruction": instruction.strip()})
    except Exception as exc:
        logger.error("Search intent parsing failed: %s", exc)
        return SearchIntent(keyword="udgu", conditions=[instruction.strip()])

    keyword = intent.keyword.strip()
    conditions: List[SearchCondition] = []
    for cond in intent.conditions:
        if not cond.value:
            continue
        conditions.append(SearchCondition(cond.name.strip(), cond.value.strip(), cond.apply_via))

    return SearchIntent(keyword=keyword, conditions=conditions)
    

def build_search_keyword(self, instruction: str) -> str:
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
        if condition.apply_via == "keyword" and condition.value:
            keyword_parts.append(condition.value.strip())

    return " ".join(part for part in keyword_parts if part)


