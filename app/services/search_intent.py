from dataclasses import dataclass
from typing import List
from loguru import logger
from pydantic import BaseModel, Field
from app.prompts.prompts import INTENT_PROMPT
from app.services.llm_engine import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


class SearchIntentSchema(BaseModel):
    keyword: str 
    conditions: List[str] = Field(default_factory=list)

@dataclass
class SearchIntent:
    keyword: str
    conditions: List[str]

def build_search_intent(instruction: str) -> SearchIntent:
    prompt = PromptTemplate.from_template(INTENT_PROMPT)
    llm = get_llm()
    parser = PydanticOutputParser(pydantic_object=SearchIntentSchema)
    chain = prompt | llm | parser

    logger.info("Requesting search intent from LLM")
    try:
        intent = chain.invoke({"instruction": instruction.strip()})
    except Exception as exc:
        logger.warning("Search intent parsing failed: %s", exc)
        return SearchIntent(keyword="udgu", conditions=[instruction.strip()])

    keyword = intent.keyword or "udgu"
    conditions = intent.conditions or []

    keyword = keyword.strip() or "udgu"
    conditions = [c.strip() for c in conditions if isinstance(c, str) and c.strip()]

    return SearchIntent(keyword=keyword, conditions=conditions)
    


