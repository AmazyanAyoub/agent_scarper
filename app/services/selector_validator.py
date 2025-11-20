"""Utilities for validating candidate search input selectors."""

from __future__ import annotations

import asyncio  # add at top

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from app.core.logger import get_logger
logger = get_logger(__name__)

from playwright.async_api import TimeoutError, Page, Locator

from app.services.session_store import SessionStore
from app.services.fetcher import _create_stealth_context, _get_playwright


@dataclass
class SelectorValidator:
    wait_for_selector: int = 10000
    navigation_timeout: int = 60000
    post_submit_wait: int = 5000

    def __post_init__(self) -> None:
        self._session_store = SessionStore()

    async def validate_and_submit(self, url: str, selectors: Iterable[str], keyword: str, skip_validation: bool) -> Optional[Tuple[str, str]]:

        storage_state_path = self._session_store.storage_state_path(url)

        p = await _get_playwright()
        browser, context, page = await _create_stealth_context(
            p, storage_state_path if self._session_store.has(url) else None
        )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout)

            for selector in dict.fromkeys(selectors):
                logger.info("Validating selector '%s'", selector)
                if skip_validation:
                    try:
                        handle = await page.wait_for_selector(selector, timeout=self.wait_for_selector)
                    except TimeoutError:
                        logger.warning("Selector '%s' not found during skip-validation path", selector)
                        continue
                else:
                    handle = await self._get_valid_handle(page, selector)
                    if not handle:
                        logger.warning("Selector '%s' failed validation", selector)
                        continue
                await self._fill_and_submit(handle, keyword)
                await self._await_results(page)
                await self._scroll_results(page)
                html = await page.content()
                await context.storage_state(path=storage_state_path)
                logger.info("Selector '%s' validated and submitted successfully", selector)
                return selector, html
            
        finally:
            try:
                await context.close()
            except Exception:
                logger.warning("Playwright context failed to close cleanly")

        return None


    async def _await_results(self, page: Page) -> None:
        selectors = [
            ".srp-results",
            ".s-item",
            "[data-testid='listing']",
            "[data-component-type='s-search-result']",
        ]
        tasks = [asyncio.create_task(page.wait_for_selector(s, timeout=self.post_submit_wait)) for s in selectors]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        try:
            await page.wait_for_load_state("networkidle", timeout=self.post_submit_wait)
        except TimeoutError:
            logger.warning("Timed out waiting for network idle; continuing with current HTML")

    
    async def _scroll_results(self, page: Page, step_px: int = 1200, repeats: int = 4, pause_ms: int = 800) -> None:
        for _ in range(repeats):
            await page.mouse.wheel(0, step_px)          # scroll down
            await page.wait_for_timeout(pause_ms)       # give content time to render
        await page.wait_for_timeout(pause_ms)           # final settle


    async def _get_valid_handle(self, page: Page, selector: str) -> Optional[Locator]:

        loc = page.locator(selector).first
        try:
            await loc.wait_for(state="visible", timeout=self.wait_for_selector)
        except TimeoutError:
            return None
        if not await loc.is_enabled():
            return None
        # no pre-fill here; we fill once in _fill_and_submit
        return loc
        # try:
        #     handle = await page.wait_for_selector(selector, timeout=self.wait_for_selector)
        # except TimeoutError:
        #     return False
        # if handle is None:
        #     return False

        # visible = await handle.is_visible()
        # enabled = await handle.is_enabled()

        # if not (visible and enabled):
        #     return False

        # try:
        #     await handle.fill("")
        # except Exception:
        #     return False

        # return handle

    async def _fill_and_submit(self, handle, keyword: str) -> None:
        await handle.click()
        await handle.fill(keyword)  # instant value set triggers input events
        await handle.press("Enter")
