import asyncio
from loguru import logger

from app.services.crawler import crawl_site_step
from app.services.rank import rank_candidates
from app.services.exporter import export_results
from app.models.state import ScraperState
from app.core.config import OUTPUT_DIR


def crawl_node(state: ScraperState) -> ScraperState:
    visited = state.get("visited", set())
    frontier = state.get("frontier", [state["url"]])
    depth = state.get("depth", 0)

    logger.info(f"[Depth {depth}] Crawling {len(frontier)} pages")

    candidate_pages, visited, new_frontier = asyncio.run(
        crawl_site_step(frontier, visited)
    )

    # Update state
    state["candidate_pages"] = candidate_pages
    state["visited"] = visited
    state["frontier"] = new_frontier
    state["depth"] = depth + 1

    logger.info(f"🌐 Depth {state['depth']} finished. "
                f"Found {len(candidate_pages)} candidate pages.")
    return state


def rank_node(state: ScraperState, top_k: int = 5) -> ScraperState:
    candidates = state.get("candidate_pages", [])
    instruction = state.get("instruction", "")

    if not candidates:
        logger.warning("No candidates to score.")
        return state
    
    ranked = rank_candidates(candidates, instruction, top_k=top_k)
    state["ranked_links"] = ranked

    return state


def export_node(state: ScraperState, output_dir: str = OUTPUT_DIR, formats: list = ["json", "csv"]) -> ScraperState:
    """
    Node wrapper for exporting ranked results.
    Exports state["ranked_links"] into JSON/CSV.
    """
    ranked = state.get("ranked_links", [])

    if not ranked:
        logger.warning("⚠️ No ranked results found in state, nothing to export.")
        return state

    export_results(ranked, output_dir=output_dir, formats=formats)
    logger.success("✅ Export completed successfully.")

    return state

def no_results_node(state: ScraperState) -> ScraperState:
    """
    Node executed when no verified links are found and
    crawling cannot continue (max depth reached or no more links).
    """
    logger.warning("❌ No verified results found. Crawling stopped.")
    
    # Optional: mark in state so downstream systems know why we stopped
    state["status"] = "no_results"
    state["verified_links"] = []
    
    return state