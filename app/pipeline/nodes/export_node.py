from loguru import logger
from app.models.state import ScraperState
from app.services.exporter import export_results
from app.core.config import OUTPUT_DIR
from app.services.filter_links import filter_links


def export_node(state: ScraperState, output_dir: str = OUTPUT_DIR, formats: list = ["json", "csv"]) -> ScraperState:
    """
    Node wrapper for exporting ranked results.
    Exports state["ranked_links"] into JSON/CSV.
    """
    verified_links = state.get("verified_links", [])

    if not verified_links:
        logger.warning("⚠️ No verified_links results found in state, nothing to export.")
        return state

    export_results(verified_links, output_dir=output_dir, formats=formats)
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


def filter_links_node(state: ScraperState) -> ScraperState:
    """
    Node: Filter the discovered links before verification.
    - Runs structural + semantic filtering.
    - Reduces frontier size for efficiency.
    """
    frontier = state.get("frontier",[{"url":"", "text":""}])
    instruction = state.get("instruction", str)
    url = state.get("url")

    if not frontier:
        logger.warning("⚠️ No links in frontier to filter.")
        state["frontier"] = []
        return state
    
    logger.info(f"Filtering {len(frontier)} links with instruction: {instruction}")
    filtered = filter_links(frontier, instruction, url)



    state["frontier"] = [{"url": url, "text": ""} for url in filtered]
    logger.success(f"✅ Filtered frontier size: {len(state['frontier'])}")

    return state

