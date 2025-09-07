from typing import Dict, Any, TypedDict, List, Optional


class ScraperState(TypedDict):
    url: str
    instruction: str
    html: Optional[str]
    text: Optional[str]
    chunks: Optional[List[str]]
    prompt: Optional[str]
    llm_response: Optional[str]
    parsed_data: Optional[Dict[str, Any]]