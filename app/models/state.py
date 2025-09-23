from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ScraperState:
    # Input info
    url: str
    instruction: str
    
    # Crawler control
    depth: int = 0
    max_depth: int = 3
    batch_index: int = 0
    max_batches: int = 5
    
    # Link tracking
    visited_links: set = field(default_factory=set)
    frontier: List[str] = field(default_factory=list)
    candidate_pages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Results
    verified_results: List[Dict[str, Any]] = field(default_factory=list)
    target_results: int = 10
    
    # Status & metadata
    status: str = "initializing"
    site_type: Optional[str] = None
    errors: List[str] = field(default_factory=list)


    def add_frontier(self, links: List[str]):
        """Add new links to frontier, avoiding duplicates."""
        new_links = [link for link in links if link not in self.visited_links]
        self.frontier.extend(new_links)

    def mark_visited(self, link: str):
        """Mark a link as visited."""
        self.visited_links.add(link)

    def add_candidate_page(self, url: str, content: str):
        """Add a crawled page to candidate pages."""
        self.candidate_pages.append({"url": url, "content": content})

    def add_verified_result(self, url: str, content: str, score: float = 1.0):
        """Add a verified result page."""
        self.verified_results.append({"url": url, "content": content, "score": score})

    def set_status(self, new_status: str):
        """Update the status of the scraper."""
        self.status = new_status