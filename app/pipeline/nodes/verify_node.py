from loguru import logger
from app.models.state import ScraperState
from app.services.llm_engine import get_llm


def verify_html_node(state: ScraperState) -> ScraperState:
    """
    Ask the LLM to verify if the html pages match the user instruction.
    Keeps only the verified ones in state["verified_links"].
    """
    instruction = state["instruction"]
    candidates = state["candidate_pages"]
    verified_links = state.get("verified_links", [])

    if not candidates:
        logger.warning("⚠️ No candidate page to verify.")
        return state
    
    llm = get_llm()

    cand = candidates[0]
    url = cand.get("url")
    text = cand.get("text")

    print(f"PASSED TEXT: {text[:200]}")
    prompt = f"""
    You are an expert assistant verifying if a web page is relevant to the user request. 

    - Be generous: if the document has partial but useful information, count it as YES.  
    - Consider synonyms, related terms, and paraphrased expressions.  
    - Only say NO if the document is clearly unrelated.  

    User request:
    {instruction}

    Document (URL: {url}):
    {text[:2000]}  # truncated for efficiency

    Answer strictly with YES or NO. Do not explain.
    """
    response = llm.invoke(prompt)

    answer = response.content.strip().lower()

    if "yes" in answer:
        cand["verified"] = True
        verified_links.append(cand)
        logger.success(f"✅ Verified relevant: {url}")

    else:
        cand["verified"] = False
        logger.info(f"❌ Rejected: {url}")

    state["verified_links"] = verified_links
    logger.info(f"Verification complete: {len(verified_links)} total relevant so far.")
    
    return state        




# def verify_node(state: ScraperState, top_k: int = 3) -> ScraperState:
#     """
#     Ask the LLM to verify if the ranked pages match the user instruction.
#     Keeps only the verified ones in state["verified_links"].
#     """
#     instruction = state.get("instruction", "")
#     ranked = state.get("ranked_links", [])

#     if not ranked:
#         logger.warning("⚠️ No ranked results to verify.")
#         state["verified_links"] = []
#         return state

#     llm = get_llm()  # switchable (Ollama, OpenAI, etc.)

#     verified = []
#     for cand in ranked[:top_k]:
#         url = cand.get("url", "")
#         text = cand.get("text", "")

#         prompt = (
#             f"You are verifying if a document matches the user request.\n\n"
#             f"User request:\n{instruction}\n\n"
#             f"Document (URL: {url}):\n{text[:1500]}\n\n"
#             "(Text truncated for efficiency)\n\n"
#             "Answer YES if this document is relevant, otherwise NO."
#         )

#         response = llm.invoke(prompt)
#         answer = response.content.strip().lower()

#         if answer.startswith("yes"):
#             cand["verified"] = True
#             verified.append(cand)
#             logger.success(f"✅ Verified relevant: {url}")
#         else:
#             cand["verified"] = False
#             logger.info(f"❌ Rejected: {url}")

#     state["verified_links"] = verified
#     logger.info(f"Verification complete: {len(verified)}/{min(len(ranked), top_k)} relevant.")
#     return state
