from loguru import logger
from app.models.state import ScraperState
from app.services.llm_engine import get_llm

def verify_node(state: ScraperState, top_k: int = 3) -> ScraperState:
    """
    Ask the LLM to verify if the ranked pages match the user instruction.
    Keeps only the verified ones in state["verified_links"].
    """
    instruction = state.get("instruction", "")
    ranked = state.get("ranked_links", [])

    if not ranked:
        logger.warning("⚠️ No ranked results to verify.")
        state["verified_links"] = []
        return state

    llm = get_llm(provider="groq")  # switchable (Ollama, OpenAI, etc.)

    verified = []
    for cand in ranked[:top_k]:
        url = cand.get("url", "")
        text = cand.get("text", "")

        prompt = (
            f"You are verifying if a document matches the user request.\n\n"
            f"User request:\n{instruction}\n\n"
            f"Document (URL: {url}):\n{text[:1500]}\n\n"
            "(Text truncated for efficiency)\n\n"
            "Answer YES if this document is relevant, otherwise NO."
        )

        response = llm.invoke(prompt)
        answer = response.content.strip().lower()

        if answer.startswith("yes"):
            cand["verified"] = True
            verified.append(cand)
            logger.success(f"✅ Verified relevant: {url}")
        else:
            cand["verified"] = False
            logger.info(f"❌ Rejected: {url}")

    state["verified_links"] = verified
    logger.info(f"Verification complete: {len(verified)}/{min(len(ranked), top_k)} relevant.")
    return state
