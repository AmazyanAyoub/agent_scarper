# fetcher.py

import httpx
from playwright.async_api import async_playwright
from loguru import logger
import traceback

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


async def fetch_html_playwright(url: str, wait: int = 3000) -> str:
    """
    Fetch renderd HTML using playwright.
    Best for heavy JS pages.
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
            return html
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {repr(e)}")
        logger.error(traceback.format_exc())
        return ""
    
# if __name__ == "__main__":
#     import asyncio
#     url = "https://quotes.toscrape.com/js/"
#     html = asyncio.run(fetch_html_playwright(url))
#     print(html)

