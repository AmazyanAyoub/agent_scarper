import traceback
from playwright.async_api import async_playwright
from loguru import logger
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util

async def extract_links_dynamic(url: str, wait: int = 5000) -> list:
    """
    Extract all links from a page using Playwright (dynamic HTML).
    Returns list of dicts: {"url": ..., "text": ...}
    """

    try:
        logger.info(f"Crawling links from {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_timeout(wait)
            html = await page.content()

            soup = BeautifulSoup(html, "html.parser")
            links = []

            for a in soup.find_all("a", href=True):
                link_url = a["href"]
                link_text = a.get_text(strip=True)
                if link_url.startswith("/"):
                    link_url = url.rstrip("/") + link_url
                links.append({"url": link_url, "text": link_text})
            await browser.close()
            logger.info(f"Found {len(links)} links (dynamic).")
            return links
    except Exception as e:
        logger.error(f"Dynamic link extraction failed: {repr(e)}")
        logger.error(traceback.format_exc())
        return []
    
def score_links_embedding(links: list, user_instruction: str, top_k: int = 3) -> list:
    """
    Score links by semantic similarity using embeddings.
    Returns top_k best matches sorted by cosine similarity.
    """

    logger.info("Scoring links by semantic similarity using embeddings.")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    candidates = [f"{link.get('text', '')} {link.get('url', '')}" for link in links]

    instruction_emb = model.encode(user_instruction, convert_to_tensor=True)
    candidates_emb = model.encode(candidates, convert_to_tensor=True)

    scores = util.cos_sim(instruction_emb, candidates_emb)[0].cpu().tolist()

    for i, link in enumerate(links):
        link['score'] = scores[i]

    top_links = sorted(links, key=lambda x: x['score'], reverse=True)[:top_k]
    logger.info(f"Top {top_k} links selected based on semantic similarity.")
    return top_links

