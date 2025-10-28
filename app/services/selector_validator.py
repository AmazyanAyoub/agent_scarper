"""Utilities for validating candidate search input selectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from loguru import logger
from playwright.async_api import TimeoutError, async_playwright, Page

from app.services.fetcher import _create_stealth_context
from app.services.session_store import SessionStore


@dataclass
class SelectorValidator:
    wait_for_selector: int = 10000
    navigation_timeout: int = 60000
    post_submit_wait: int = 5000

    def __post_init__(self) -> None:
        self._session_store = SessionStore()

    async def validate_and_submit(self, url: str, selectors: Iterable[str], keyword: str, skip_validation: bool) -> Optional[Tuple[str, str]]:
        # selector_list = self._deduplicate(selectors)
        # if not selector_list:
        #     return None

        storage_state_path = self._session_store.storage_state_path(url)

        async with async_playwright() as p:
            browser, context, page = await _create_stealth_context(
                p, storage_state_path if self._session_store.has(url) else None
            )

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout)

                for selector in selectors:
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
                    await self._fill_and_submit(page, handle, keyword)
                    await self._await_results(page)
                    await self._scroll_results(page)
                    html = await page.content()
                    await context.storage_state(path=storage_state_path)
                    logger.success("Selector '%s' validated and submitted successfully", selector)
                    return selector, html
                
            finally:
                try:
                    await browser.close()
                except Exception:
                    logger.warning("Playwright browser failed to close cleanly")
        return None


    async def _await_results(self, page: Page) -> None:
        result_selectors = [
            ".srp-results",
            ".s-item",
            "[data-testid='listing']",
            "[data-component-type='s-search-result']",
        ]
        for selector in result_selectors:
            try:
                await page.wait_for_selector(selector, timeout=self.post_submit_wait)
                break
            except TimeoutError:
                continue
        try:
            await page.wait_for_load_state("networkidle", timeout=self.post_submit_wait)
        except TimeoutError:
            logger.warning("Timed out waiting for network idle; continuing with current HTML")

    # def _deduplicate(self, selectors: Iterable[str]) -> list[str]:
    #     seen = set()
    #     unique = []
    #     for selector in selectors:
    #         if not selector or selector in seen:
    #             continue
    #         seen.add(selector)
    #         unique.append(selector)
    #     return unique
    
    async def _scroll_results(self, page: Page, step_px: int = 1200, repeats: int = 4, pause_ms: int = 800) -> None:
        for _ in range(repeats):
            await page.mouse.wheel(0, step_px)          # scroll down
            await page.wait_for_timeout(pause_ms)       # give content time to render
        await page.wait_for_timeout(pause_ms)           # final settle


    async def _get_valid_handle(self, page: Page, selector: str) -> bool:
        try:
            handle = await page.wait_for_selector(selector, timeout=self.wait_for_selector)
        except TimeoutError:
            return False
        if handle is None:
            return False

        visible = await handle.is_visible()
        enabled = await handle.is_enabled()

        if not (visible and enabled):
            return False

        try:
            await handle.fill("")
        except Exception:
            return False

        return handle

    async def _fill_and_submit(self, page: Page, handle, keyword: str) -> None:
        await handle.click()
        await handle.fill("")
        await handle.type(keyword, delay=50)
        await handle.press("Enter")