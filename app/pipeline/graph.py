# Graph.py
import asyncio
from loguru import logger
from langgraph.graph import StateGraph, END
from app.pipeline.nodes.crawl_node import crawl_html_node, crawl_links_node, seed_node
from app.pipeline.nodes.verify_node import verify_html_node
from app.pipeline.nodes.export_node import export_node, no_results_node, filter_links_node
from app.models.state import ScraperState
# from app.core.config import MAX_DEPTH

# def decide_next_step(state: ScraperState) -> str:
#     """
#     Decide what happens after verify_node:
#     - Export if we have verified links
#     - Continue crawling if depth < MAX_DEPTH
#     - Stop with no_results otherwise
#     """
#     verified = state.get("verified_links", [])
#     depth = state.get("depth", 0)

#     if verified:
#         return "export"
#     elif depth < MAX_DEPTH:
#         return "crawl"
#     else:
#         return "no_results"
    

# def build_scraper_graph():
#     graph = StateGraph(ScraperState)

#     graph.add_node("crawl", crawl_node)
#     graph.add_node("rank", rank_node)
#     graph.add_node("verify", verify_node)
#     graph.add_node("export", export_node)
#     graph.add_node("no_results", no_results_node)

#     graph.set_entry_point("crawl")

#     graph.add_edge("crawl", "rank")
#     graph.add_edge("rank", "verify")

#     graph.add_conditional_edges(
#         "verify",
#         decide_next_step,
#         {
#             "export": "export",
#             "crawl": "crawl",
#             "no_results": "no_results"
#         }       
#     )

#     graph.add_edge("export", END)
#     graph.add_edge("no_results", END)

#     return graph.compile()


def build_scraper_graph(target_results: int = 3, top_k: int = 3, MAX_DEPTH: int = 3):
    graph = StateGraph(ScraperState)

    # Register nodes
    graph.add_node("seed", seed_node)
    graph.add_node("verify_html", verify_html_node)
    graph.add_node("verify_html_second", verify_html_node)
    graph.add_node("crawl_links", crawl_links_node)
    graph.add_node("filter_links", filter_links_node)
    graph.add_node("crawl_html", crawl_html_node)
    graph.add_node("export", export_node)
    graph.add_node("no_results", no_results_node)

    # Entry point: seed first
    graph.set_entry_point("seed")
    graph.add_edge("seed", "verify_html")

    # --- Conditional after seed verification ---
    def verify_html_condition(state: ScraperState):
        verified = len(state.get("verified_links", []))
        depth = state.get("depth", 0)

        if verified >= target_results:
            return "export"
        elif depth < MAX_DEPTH:
            return "crawl_links"
        else:
            return "no_results"

    graph.add_conditional_edges(
        "verify_html",
        verify_html_condition,
        {
            "export": "export",
            "crawl_links": "crawl_links",
            "no_results": "no_results"
        }
    )

    # Links flow
    graph.add_edge("crawl_links", "filter_links")
    graph.add_edge("filter_links", "crawl_html")
    graph.add_edge("crawl_html","verify_html_second")

    # --- Conditional after crawl_html batch ---
    def batch_condition(state: ScraperState):
        verified = len(state.get("verified_links", []))
        frontier = state.get("frontier", [])
        batch_index = state.get("batch_index", 0)
        depth = state.get("depth", 0)

        if verified >= target_results:
            return "export"
        elif batch_index * top_k < len(frontier):
            return "crawl_html"  # next batch in current depth
        elif depth < MAX_DEPTH:
            return "crawl_links"  # dive deeper from verified links
        elif verified > 0:
            return "export"
        else:
            return "no_results"

    graph.add_conditional_edges(
        "verify_html_second",
        batch_condition,
        {
            "export": "export",
            "crawl_html": "crawl_html",   # loop to itself
            "crawl_links": "crawl_links", # dive deeper
            "no_results": "no_results"
        }
    )

    # End
    graph.add_edge("export", END)
    graph.add_edge("no_results", END)

    return graph.compile()