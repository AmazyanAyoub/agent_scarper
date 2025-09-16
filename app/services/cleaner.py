# cleaner.py

from bs4 import BeautifulSoup
from loguru import logger
import re
import traceback

def extract_main_content(html: str) -> str:
    """
    Extract the main readable content from HTML.
    Prioritizes <main> or <article>, falls back to densest <div>.
    Removes boilerplate and low-quality junk.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove obvious junk
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form", "iframe"]):
            tag.decompose()

        # 1. Try <main> or <article>
        main = soup.find("main") or soup.find("article")
        if main:
            text = main.get_text(" ", strip=True)
            if len(text) > 300:
                return re.sub(r"\s+", " ", text)

        # 2. Fallback: densest <div>
        candidates = soup.find_all("div")
        best_text, max_len = "", 0
        for div in candidates:
            t = div.get_text(" ", strip=True)
            if len(t) > max_len:
                best_text, max_len = t, len(t)

        text = best_text if best_text else soup.get_text(" ", strip=True)

        # Final cleanup
        text = re.sub(r"\s+", " ", text)

        # Quality check: drop junky pages
        if len(text) < 300:
            return ""

        logger.info("Html cleaned Successfully")
        return text

    except Exception as e:
        logger.error(f"Could not clean HTML due to: {repr(e)}")
        logger.error(traceback.format_exc())
        return ""

    
# def chunk_html(text: str, max_chars: int = 1000, overlap: int = 100) -> list:
#     """
#     Split long text into smaller chunks.
#     Useful for LLM input (avoids context overflow).
#     """

#     try:
#         chunks = []
#         logger.info(f"Chunking html into list")
#         for i in range(0, len(text), max_chars - overlap):
#             chunks.append(text[i:i + max_chars])
#         return chunks
#     except Exception as e:
#         logger.error(f"chunking failed due to: {repr(e)}")
#         logger.error(traceback.format_exc())
#         return ""
