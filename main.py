import asyncio

from app.core.logger import get_logger, setup_logging
from app.pipeline.graph import build_agent_graph

logger = get_logger(__name__)


def run_agent(url: str, instruction: str, log_level: str = "INFO") -> None:
    setup_logging(log_level=log_level.upper())

    graph = build_agent_graph()
    state = {
        "url": url,
        "instruction": instruction,
        "errors": [],
        "metadata": {},
    }

    logger.info("Starting agent run for %s", url)
    result = asyncio.run(graph.ainvoke(state))

    site_type = result.get("site_type")
    cards = result.get("cards") or []
    logger.info("Agent finished with site_type=%s, cards=%d", site_type, len(cards))

    output_path = (result.get("metadata") or {}).get("output_path")
    if output_path:
        logger.info("Results saved to %s", output_path)

    for err in result.get("errors", []):
        logger.error("Error: %s", err)


if __name__ == "__main__":
    URL = "https://www.ebay.com"
    INSTRUCTION = "Find iPhone 15"
    run_agent(URL, INSTRUCTION, log_level="INFO")
