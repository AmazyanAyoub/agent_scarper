# Graph.py
import asyncio
from loguru import logger
from langgraph.graph import StateGraph, END
from nodes.crawl_node import crawl_node, rank_node, export_node, no_results_node
from nodes.verify_node import verify_node
from app.models.state import ScraperState
from app.core.config import MAX_DEPTH

def decide_next_step(state: ScraperState) -> str:
    """
    Decide what happens after verify_node:
    - Export if we have verified links
    - Continue crawling if depth < MAX_DEPTH
    - Stop with no_results otherwise
    """
    verified = state.get("verified_links", [])
    depth = state.get("depth", 0)

    if verified:
        return "export"
    elif depth < MAX_DEPTH:
        return "crawl"
    else:
        return "no_results"
    

def build_scraper_graph():
    graph = StateGraph(ScraperState)

    graph.add_node("crawl", crawl_node)
    graph.add_node("rank", rank_node)
    graph.add_node("verify", verify_node)
    graph.add_node("export", export_node)
    graph.add_node("no_results", no_results_node)

    graph.set_entry_point("crawl")

    graph.add_edge("crawl", "rank")
    graph.add_edge("rank", "verify")

    graph.add_conditional_edges(
        "verify",
        decide_next_step,
        {
            "export": "export",
            "crawl": "crawl",
            "no_results": "no_results"
        }       
    )

    graph.add_edge("export", END)
    graph.add_edge("no_results", END)

    return graph.compile()