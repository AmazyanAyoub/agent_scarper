import re
import tldextract
from urllib.parse import urljoin, urlparse
from typing import List, Dict
from sentence_transformers import SentenceTransformer, util
from loguru import logger

embed = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')

BLOCK_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".pdf",
    ".zip", ".tar", ".gz", ".rar", ".css", ".js", ".woff", ".mp4", ".avi"
)

BLOCK_KEYWORDS = (
    "login", "signup", "register", "cart", "checkout", "privacy", "terms", "policy", "ads", "about"
)

def filter_links(links: List[Dict[str, str]], instruction: str, base_url: str, max_links: int = 100) -> List[str]:
    """
    Universal link filter:
    1. Syntax filter
    2. Domain/scope filter
    3. Keyword relevance
    4. Embedding similarity
    5. Priority sorting
    """

    logger.info("Filtering links is on")

    filtered = []
    base_domain = tldextract.extract(base_url).registered_domain

    instr_embed = embed.encode(instruction, convert_to_tensor=True)

    for link in links:
        href = link["url"]
        text = link["text"]

        href = urljoin(base_url, href)
        parsed = urlparse(href)

        if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        if parsed.fragment:  # skip anchors (#section)
            continue
        if any(href.lower().endswith(ext) for ext in BLOCK_EXTENSIONS):
            continue

        link_domain = tldextract.extract(href).registered_domain
        if link_domain != base_domain:
            continue  # stay in domain for now

        if any(kw in href.lower() for kw in BLOCK_KEYWORDS):
            continue


        url_slug = parsed.path.lower().replace("-", " ").replace("_", " ")
        anchor_text = text.lower()

        keyword_match = sum(
            kw in url_slug or kw in anchor_text
            for kw in instruction.lower().split()
        )

        cand_embed = embed.encode(url_slug+" "+anchor_text, convert_to_tensor=True)
        sim_cos = float(util.cos_sim(instr_embed, cand_embed).item())

        final_score = keyword_match * 0.5 + sim_cos

        filtered.append({"url": href, "score": final_score})

    filtered = sorted(filtered, key=lambda x: x["score"], reverse=True)
    filtered = filtered[:max_links]

    return [f["url"] for f in filtered]