from typing import Dict, Any, TypedDict, List, Optional


class ScraperState(TypedDict):
    # User input
    url: str
    instruction: str

    # Page content
    html: Optional[str]
    text: Optional[str]
    chunks: Optional[List[str]]

    # LLM interaction
    prompt: Optional[str]
    llm_response: Optional[str]
    parsed_data: Optional[Dict[str, Any]]

    # Crawl metadata
    links: Optional[List[Dict[str, Any]]]
    depth: Optional[int]
    visited_urls: Optional[List[str]]
    selected_url: Optional[List[Dict[str, Any]]]