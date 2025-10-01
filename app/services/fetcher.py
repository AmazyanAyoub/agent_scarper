# fetcher.py

from playwright.async_api import async_playwright
from loguru import logger
from playwright_stealth import Stealth 
from pathlib import Path
import traceback, asyncio

# from bs4 import BeautifulSoup
from typing import Optional
from app.services.captcha_manager import CaptchaManager, CaptchaDetected, CaptchaDecision
from app.services.session_store import SessionStore
import nodriver as uc
from app.core.config import BROWSER_ARGS, VIEWPORT, USER_AGENT

captcha_manager = CaptchaManager()
session_store = SessionStore()

async def _create_stealth_context(playwright, storage_state_path: Optional[str] = None):
    browser = await playwright.chromium.launch(
        headless=True,
        args=BROWSER_ARGS,
        channel="chrome",
    )

    context_kwargs = {
        "viewport": VIEWPORT,
        "user_agent": USER_AGENT,
        "locale": "en-US",
        "timezone_id": "America/New_York",
    }

    if storage_state_path and Path(storage_state_path).exists():
        context_kwargs["storage_state"] = storage_state_path

    context = await browser.new_context(**context_kwargs)

    stealth = Stealth()
    await stealth.apply_stealth_async(context)

    page = await context.new_page()
    await stealth.apply_stealth_async(page)

    return browser, context, page

async def wait_until_done_or_timeout(seconds: int):
    try:
        done, _ = await asyncio.wait(
            [asyncio.to_thread(input, "Press Enter when done: ")],
            timeout=seconds
        )
        return True if done else False
    except Exception:
        return False

async def _manual_solve(url: str, wait: int) -> str:
    """Open a manual session, capture storage_state to disk, and return its path."""
    logger.warning(
        "Opening manual solve window for %s. Complete the captcha in the browser before the timeout.",
        url,
    )

    browser = None

    try:
        browser = await uc.start()
        page = await browser.get(url)

        # manual_wait_seconds = wait
        # if timeout:
        #     manual_wait_seconds = max(manual_wait_seconds, int(timeout / 1000))

        await wait_until_done_or_timeout(wait)

        origin = await page.evaluate("window.location.origin")
        cookies = await browser.cookies.get_all()
        local_storage_items = await page.get_local_storage()

        cookies_formatted = [
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "expires": cookie.expires if cookie.expires is not None else -1,
                "httpOnly": cookie.http_only,
                "secure": cookie.secure,
                "sameSite": cookie.same_site.name.capitalize() if cookie.same_site else "Lax",
            }
            for cookie in cookies
        ]

        local_storage = [
            {"name": key, "value": value}
            for key, value in local_storage_items.items()
        ]

        storage_state = {
            "cookies": cookies_formatted,
            "origins": [
                {
                    "origin": origin,
                    "localStorage": local_storage,
                }
            ],
        }

        session_store.import_storage_state(url, storage_state)
        logger.info("Session stored after manual solve for %s.", url)

    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                logger.warning("Manual solve browser failed to stop cleanly.")


async def _apply_solver_service(url: str) -> None:
    logger.warning("Solver service not configured; skipping automated solve for %s", url)


async def fetch_html(
    url: str,
    wait: int = 3000,
    *,
    timeout: Optional[int] = None,
    attempt: int = 0
) -> str:
    # if attempt >= max_attempts:
    #     logger.error("Max captcha attempts reached for %s; aborting fetch.", url)
    #     return ""
    # attempt_1 = 0
    storage_state_path = session_store.storage_state_path(url)

    storage_state = None

    try:
        logger.info("Fetching html with playwright: %s", url)

        async with async_playwright() as p:
            browser, context, page = await _create_stealth_context(p, storage_state_path)
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(wait)
            html = await page.content()
            storage_state = await context.storage_state()
            await browser.close()

        captcha_manager.handle(url, html)
        if storage_state:
            session_store.save(url, storage_state)
        return html

    except CaptchaDetected as captcha_error:
        logger.warning(str(captcha_error))

        if captcha_error.decision == CaptchaDecision.reuse_session and Path(storage_state_path).exists():
            if attempt == 0:
                logger.info("Retrying %s with stored session.", url)
                return await fetch_html(url, wait, timeout=timeout, attempt=attempt + 1)
            logger.info("Stored session failed for %s; escalating to manual solve.", url)
            await _manual_solve(url, wait)
            return await fetch_html(url, wait, timeout=timeout, attempt=attempt + 1)

        if captcha_error.decision == CaptchaDecision.manual_solve:
            await _manual_solve(url, wait)
            return await fetch_html(url, wait, timeout=timeout, attempt=attempt + 1)

        # if captcha_error.decision == CaptchaDecision.solver_service:
        #     await _apply_solver_service(url)
        #     return await fetch_html(url, wait, timeout=timeout, attempt=attempt + 1)

        # logger.error("Captcha decision '%s' led to abort for %s.", captcha_error.decision, url)
        return ""

    except Exception as e:
        logger.error("Playwright fetch failed for %s: %r", url, e)
        logger.error(traceback.format_exc())
        return ""

# def fetch_links(html: str, url: str) -> List[Dict]:
#     """
#     Extract all links from a page using Playwright (dynamic HTML).
#     Returns list of dicts: {"url": ..., "text": ...}
#     """

#     try:
#         logger.info(f"Fetching URL with playwright: {url}")
#         soup = BeautifulSoup(html, "html.parser")
#         links = []
#         for p in soup.find_all("a", href=True):
#             link_url = p["href"]
#             link_text = p.get_text(strip=True)
#             if link_url.startswith("/"):
#                 link_url = url.rstrip("/") + link_url
#             links.append({"url": link_url, "text": link_text})

#         return links
#     except Exception as e:
#         logger.error(f"Playwright fetch failed for {url}: {repr(e)}")
#         logger.error(traceback.format_exc())
#         return []

