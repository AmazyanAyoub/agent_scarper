from typing import TypedDict, Optional, List, Dict, Any, Set

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
    visited_links: Optional[Set[str]]   # for crawl_links (just discovery)
    visited_html_links: Optional[Set[str]]    # for crawl_html (actual HTML scraping)
    frontier: Optional[List[Dict[str, str]]]        # current frontier of URLs to crawl
    depth: int                           # current BFS depth

    # Multi-page results
    candidate_pages: Optional[List[Dict[str, Any]]]   # raw {url, text}
    ranked_links: Optional[List[Dict[str, Any]]]      # {url, text, score}
    verified_links: Optional[List[Dict[str, Any]]]    # LLM-confirmed relevant
    selected_url: Optional[str]
    batch_index: int

    # Status
    status: Optional[str]                # e.g. "ok", "no_results"
