# parser.py

import json
import re

from loguru import logger
from pydantic import ValidationError
from app.models.extraction import ExtractionResult


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