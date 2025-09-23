# parser.py

import json
import re
from typing import Iterable  # keep next to existing imports
from loguru import logger
from pydantic import ValidationError
from app.models.extraction import ExtractionResult
from app.services.llm_engine import get_llm
from app.prompts.prompts import SEARCH_SELECTOR_PROMPT
from bs4 import BeautifulSoup
from bs4.element import Tag
from app.core.config import SEARCH_ATTRS, SEARCH_TERMS

def _attr_tokens(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v]
    return [str(value)]

def clean_json_text(text: str) -> str:
    """Remove markdown fences like ```json ... ``` if present."""
    text = text.strip()
    # Remove ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    return text

def validation_and_parse_response(response_text: str):
    """
    Validate and parse the LLM response as JSON.
    """

    try:
        logger.info("Parsing and validating the extracted text")
        cleaned_text = clean_json_text(response_text)
        parsed = json.loads(cleaned_text)
        result = ExtractionResult(**parsed)
        logger.info("✅ JSON validated successfully.")

        return result.dict()
    
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"❌ JSON parsing failed: {repr(e)}")
        return {"error": str(e), "raw_response": response_text}
    
def detect_search_selector_llm(html: str) -> str:
    """
    Uses LLM to detect the CSS selector of the search bar input field.
    """
    llm = get_llm()
    soup = BeautifulSoup(html, "html.parser")
    search_regex = re.compile(SEARCH_TERMS, re.I)

    snippet = None
    for form in soup.find_all("form"):
        tokens = []
        for attr in ("id", "name", "class", "aria-label", "role"):
            tokens.extend(_attr_tokens(form.get(attr)))
        if tokens and search_regex.search(" ".join(tokens)):
            snippet = form.prettify()
            break

    if snippet is None:
        form = soup.find("form", attrs={"role": "search"})
        if form:
            snippet = form.prettify()

    if snippet is None:
        input_tag = None
        for attr in ("id", "name", "placeholder", "aria-label"):
            candidate = soup.find("input", attrs={attr: search_regex})
            if candidate:
                input_tag = candidate
                break
        if input_tag:
            container = input_tag.find_parent("form") or input_tag.parent
            if container:
                snippet = container.prettify()

    if snippet is None:
        body = soup.body
        if body:
            blocks = body.find_all(["form", "div", "section", "header", "main"], limit=6)
            if blocks:
                snippet = "\n".join(block.prettify() for block in blocks)
        if not snippet:
            snippet = body.prettify() if body else ""

    if not snippet:
        snippet = html[:8000]

    snippet = snippet[:8000]

    prompt = SEARCH_SELECTOR_PROMPT.format(snippet=snippet)
    response = llm.invoke(prompt)
    return response.content.strip()


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


def detect_search_selector(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    search_regex = re.compile(SEARCH_TERMS, re.I)

    forms = []
    for form in soup.find_all("form"):
        tokens = []
        for attr in ("id", "name", "class", "aria-label", "role"):
            tokens.extend(_attr_tokens(form.get(attr)))
        attrs = " ".join(tokens).lower()
        if search_regex.search(attrs):
            forms.append(form)

    if not forms:
        forms = soup.find_all("form", role="search")

    for form in forms:
        candidate = form.find("input", attrs={"type": re.compile("search|text", re.I)})
        if not candidate:
            for attr in SEARCH_ATTRS:
                candidate = form.find("input", attrs={attr: re.compile(SEARCH_TERMS, re.I)})
                if candidate:
                    break
        if candidate:
            return build_selector(candidate)

    for attr in SEARCH_ATTRS:
        candidate = soup.find("input", attrs={attr: re.compile(SEARCH_TERMS, re.I)})
        if candidate:
            return build_selector(candidate)

    return "input"