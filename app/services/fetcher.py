# fetcher.py

import httpx
from playwright.async_api import async_playwright
from loguru import logger
import traceback
from bs4 import BeautifulSoup

def fetch_with_httpx(url: str, timeout: int = 10) -> str:
    """
    Fetch HTML using httpx.
    Best for static pages.
    """
    try:
        logger.info(f"fetching URL with httpx: {url}")
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"HTTPX fetch failed for {url}: {repr(e)}")
        logger.error(traceback.format_exc())
        return ""


async def fetch_html_links(url: str, wait: int = 3000):
    """
    Extract html and all links from a page using Playwright (dynamic HTML).
    Returns list of dicts: {"url": ..., "text": ...}
    """

    try:
        logger.info(f"Fetching URL with playwright: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_timeout(wait)  # wait for JS to load
            html = await  page.content()
            await browser.close()
            
            soup = BeautifulSoup(html, "html.parser")
            links = []
            for p in soup.find_all("a", href=True):
                link_url = p["href"]
                link_text = p.get_text(strip=True)
                if link_url.startswith("/"):
                    link_url = url.rstrip("/") + link_url
                links.append({"url": link_url, "text": link_text})

            return html, links
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {repr(e)}") # repr() more complete: it shows the error type + message.
        logger.error(traceback.format_exc())
        return "", []
    
# if __name__ == "__main__":
#     import asyncio
#     url = "https://quotes.toscrape.com/js/"
#     html = asyncio.run(fetch_html_playwright(url))
#     print(html)

