# cleaner.py

from bs4 import BeautifulSoup
from loguru import logger
import re
import traceback

def extract_main_content(html) -> str:
    """
    Clean raw HTML and extract main readable text.
    Removes scripts, styles, and common boilerplate.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        text = re.sub(r"\s+"," ", text)

        logger.info(f"Html cleaned Successfully")

        return text
    except Exception as e:
        logger.error(f"Could not clean HTML due to: {repr(e)}")
        logger.error(traceback.format_exc())
        return ""
    
def chunk_html(text: str, max_chars: int = 1000, overlap: int = 100) -> list:
    """
    Split long text into smaller chunks.
    Useful for LLM input (avoids context overflow).
    """

    try:
        chunks = []
        logger.info(f"Chunking html into list")
        for i in range(0, len(text), max_chars - overlap):
            chunks.append(text[i:i + max_chars])
        return chunks
    except Exception as e:
        logger.error(f"chunking failed due to: {repr(e)}")
        logger.error(traceback.format_exc())
        return ""
