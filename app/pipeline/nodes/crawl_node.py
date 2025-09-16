import asyncio

from loguru import logger

from app.services.crawler import crawl_links, crawl_html
from app.services.rank import rank_candidates
from app.models.state import ScraperState

def crawl_links_node(state: ScraperState) -> ScraperState:
    """
    First step: check the seed URL's content.
    If relevant → export immediately.
    Else → crawl links.
    """
    frontier = state.get("frontier", [{"url": state["url"], "text": ""}])
    visited_links = state.get("visited_links", set())
    depth = state.get("depth", 0)

    # 1. Scrape the seed content
    new_frontier, visited_links = asyncio.run(crawl_links(frontier, visited_links))

    state["frontier"] = new_frontier
    state["visited_links"] = visited_links
    state["depth"] = depth + 1

    # logger.info(
    #     f"[Depth {state['depth']}] Finished crawl_links → "
    #     f"{len(new_frontier)} links discovered | "
    #     f"Visited so far: {len(visited_links)}"
    # )
    return state


def crawl_html_node(state: ScraperState, top_k: int = 3) -> ScraperState:
    """
    Node: Crawl HTML for the next batch of links from the frontier.
    - Uses batch_index to slice frontier.
    - Scrapes only top_k URLs in this round.
    - Updates candidate_pages with new scraped pages.
    """

    frontier = state.get("frontier", [])
    visited_html = state.get("visited_html_links", set())
    batch_index = state.get("batch_index", 0)

    start = batch_index * top_k
    end = start + top_k
    batch = frontier[start:end]

    if not batch:
        logger.warning("⚠️ No more links left to crawl in frontier.")
        state["candidate_pages"] = []
        return state
    
    logger.info(
        f"📑 Crawling batch {batch_index+1}: "
        f"links {start+1} → {min(end, len(frontier))} of {len(frontier)}"
    )

    candidate_pages, visited_html, _ = asyncio.run(crawl_html(batch, visited_html))

    state["candidate_pages"] = candidate_pages
    state["visited_html"] = visited_html
    state["batch_index"] = batch_index + 1

    logger.success(
        f"✅ Batch {batch_index+1} finished. "
        f"Crawled {len(candidate_pages)} pages. "
        f"Verified so far: {len(state.get('verified_links', []))}"
    )

    return state



def seed_node(state: ScraperState):

    url = state["url"]
    visited_html_links = state.get("visited_html_links", set())
    depth = state.get("depth", 0)
    html = state.get("html", "")

    candidate_pages, visited_html, html =  asyncio.run(crawl_html([{"url": url, "text": ""}], visited_html_links))

    state["candidate_pages"] = candidate_pages
    state["visited_html"] = visited_html
    state["depth"] = depth + 1
    state["html"] = html

    return state

# def rank_node(state: ScraperState, top_k: int = 5) -> ScraperState:
#     candidates = state.get("candidate_pages", [])
#     logger.info(f"Ranking {candidates} candidates.")
#     instruction = state.get("instruction", "")

#     if not candidates:
#         logger.warning("No candidates to score.")
#         return state
    
#     ranked = rank_candidates(candidates, instruction, top_k=top_k)
#     logger.info(f"ranked {ranked} candidates selected.")
#     state["ranked_links"] = ranked

#     return state




