from __future__ import annotations

from langchain.output_parsers import PydanticOutputParser
from langchain.output_parsers.openai_functions import PydanticAttrOutputFunctionsParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.utils.function_calling import convert_to_openai_function

from app.prompts.prompts import (
    CARD_PROMPT,
    EXPANDED_CLASSIFIER_PROMPT,
    SEARCH_INTENT_PROMPT,
    SEARCH_SELECTORS_PROMPT,
)
from app.services.chains.models import CardMappingResult, SearchIntentSchema
from app.services.llm_engine import get_llm
from app.services.chains.models import WebsiteTypeClassifier


def build_site_classifier_chain():
    llm = get_llm().bind(
        functions=[convert_to_openai_function(WebsiteTypeClassifier)],
        function_call={"name": "WebsiteTypeClassifier"},
    )
    parser = PydanticAttrOutputFunctionsParser(
        pydantic_schema=WebsiteTypeClassifier,
        attr_name="site_type",
    )
    prompt = PromptTemplate.from_template(EXPANDED_CLASSIFIER_PROMPT.strip())
    return prompt | llm | parser

def build_card_mapping_chain():
    parser = PydanticOutputParser(pydantic_object=CardMappingResult)
    prompt = PromptTemplate.from_template(CARD_PROMPT.strip())
    llm = get_llm()
    return prompt | llm | parser


def build_search_intent_chain():
    parser = PydanticOutputParser(pydantic_object=SearchIntentSchema)
    prompt = PromptTemplate.from_template(SEARCH_INTENT_PROMPT.strip())
    llm = get_llm()
    return prompt | llm | parser


def build_search_selector_chain():
    prompt = PromptTemplate.from_template(SEARCH_SELECTORS_PROMPT.strip())
    llm = get_llm()
    return prompt | llm | StrOutputParser()
