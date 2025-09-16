# fetcher.py

from playwright.async_api import async_playwright
from loguru import logger
import traceback
from bs4 import BeautifulSoup
from typing import List, Dict

async def fetch_html(url: str, wait: int = 3000) -> str:
    """
    Extract html and all links from a page using Playwright (dynamic HTML).
    Returns list of dicts: {"url": ..., "text": ...}
    """

    try:
        logger.info(f"Fetching html with playwright: {url}")
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_timeout(wait)  # wait for JS to load
            html = await  page.content()
            await browser.close()

            return html
        
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {repr(e)}") # repr() more complete: it shows the error type + message.
        logger.error(traceback.format_exc())
        return "", []

def fetch_links(html: str, url: str) -> List[Dict]:
    """
    Extract html and all links from a page using Playwright (dynamic HTML).
    Returns list of dicts: {"url": ..., "text": ...}
    """

    try:
        logger.info(f"Fetching URL with playwright: {url}")
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for p in soup.find_all("a", href=True):
            link_url = p["href"]
            link_text = p.get_text(strip=True)
            if link_url.startswith("/"):
                link_url = url.rstrip("/") + link_url
            links.append({"url": link_url, "text": link_text})

        return links
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {repr(e)}")
        logger.error(traceback.format_exc())
        return []

