import asyncio
from loguru import logger

from app.services.crawler import extract_links_dynamic, score_links_embedding
from app.models.state import ScraperState

MAX_CRAWL_DEPTH = 3
SIMILARITY_THRESH = 0.75

def crawl_node(state: ScraperState) -> ScraperState:
    url = state.get("url")
    depth = state.get("depth", 0)
    state["visited_urls"] = state.get("visited_urls", set())

    logger.info(f"[Depth {depth}] Crawling: {url}")

    links = asyncio.run(extract_links_dynamic(url))

    state["links"] = links
    state["visited_urls"].add(url)

    logger.info(f"Discovered {len(links)} links on {url}")
    return state

def scoring_node(state: ScraperState) -> ScraperState:
    links = state.get("links")
    instruction = state.get("instruction")

    if not links:
        logger.warning("No links to score.")
        return state
    
    top_links = score_links_embedding(links, instruction)
    best = top_links[0]

    logger.info(f"Best link: {best['url']} (score={best['score']:.2f})")

    if best["score"] >= SIMILARITY_THRESH:
        state["selected_url"] = best["url"]
        logger.success(f"🎯 Selected target URL: {best['url']}")

    else:
        state["selected_url"] = None

    return state


def expand_node(state: ScraperState) -> ScraperState:
    visited = state.get("visited_urls", set())
    links = state.get("links", [])
    depth = state.get("depth", 0)

    if depth >= MAX_CRAWL_DEPTH:
        logger.warning("Reached max depth. Stopping crawl.")
        return state
    
    for link in links:
        candidate_url = link["url"]
        if link not in visited:
            logger

