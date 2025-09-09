from sentence_transformers import SentenceTransformer, util
from loguru import logger

embedding_model  = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')


def rank_candidates(candidates: list, user_instruction: str, top_k: int = 3) -> list:
    """
    Score links by semantic similarity using embeddings.
    Returns top_k best matches sorted by cosine similarity.
    """

    logger.info("Scoring links by semantic similarity using embeddings.")

    if not candidates:
        logger.warning("No candidate links to score.")
        return []
    

    logger.info(f"Computing embeddings for {len(candidates)} candidates and the instruction.")
    instruction_emb = embedding_model.encode(user_instruction, convert_to_tensor=True)

    text = [c["text"][:1000] for c in candidates]
    cand_emb = embedding_model.encode(text, convert_to_tensor=True)

    scores = util.cos_sim(instruction_emb, cand_emb)[0].cpu().tolist()

    for i, cand in enumerate(candidates):
        cand['score'] = scores[i]

    ranked = sorted(candidates, key=lambda x: x['score'], reverse=True)[:top_k]
    logger.info(f"Top {top_k} links selected based on semantic similarity.")
    return ranked