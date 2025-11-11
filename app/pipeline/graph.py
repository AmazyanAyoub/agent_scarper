from __future__ import annotations

import asyncio
from typing import Any, Dict, Literal

from langgraph.graph import END, StateGraph

from app.core.logger import get_logger
from app.strategies.classify_website import build_hybrid_classifier
from app.strategies.ecommerce import run_ecommerce_flow

logger = get_logger(__name__)


def _errors(state: Dict[str, Any]) -> list[str]:
    state.setdefault("errors", [])
    return state["errors"]


def _metadata(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("metadata", {})
    return state["metadata"]


async def classify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    url = state["url"]
    logger.info("Classifying site type for %s", url)
    try:
        site_type = await asyncio.to_thread(build_hybrid_classifier, url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Classification failed for %s", url)
        state["site_type"] = None
        _errors(state).append(f"classification_error: {exc}")
        return state

    state["site_type"] = site_type
    logger.info("Site type detected as %s", site_type)
    return state


async def ecommerce_node(state: Dict[str, Any]) -> Dict[str, Any]:
    url = state["url"]
    instruction = state["instruction"]
    logger.info("Running ecommerce flow for %s", url)
    try:
        context = await run_ecommerce_flow(url, instruction)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ecommerce flow failed for %s", url)
        _errors(state).append(f"ecommerce_error: {exc}")
        return state

    state["search_keyword"] = context.search_keyword
    state["cards"] = context.products or []
    if context.output_path:
        _metadata(state)["output_path"] = context.output_path

    logger.info("Ecommerce flow produced %d cards", len(state["cards"]))
    return state


def _routing_decision(state: Dict[str, Any]) -> Literal["ecommerce", "end"]:
    if state.get("site_type") == "ecommerce":
        return "ecommerce"
    return "end"


def build_agent_graph() -> StateGraph:
    graph = StateGraph(dict)

    graph.add_node("classify", classify_node)
    graph.add_node("ecommerce", ecommerce_node)
    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        _routing_decision,
        {
            "ecommerce": "ecommerce",
            "end": END,
        },
    )

    graph.add_edge("ecommerce", END)
    return graph.compile()
