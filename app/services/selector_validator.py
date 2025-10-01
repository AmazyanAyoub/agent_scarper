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
    wait_for_selector: int = 5000
    navigation_timeout: int = 60000
    post_submit_wait: int = 5000

    def __post_init__(self) -> None:
        self._session_store = SessionStore()

    async def validate_and_submit(self, url: str, selectors: Iterable[str], keyword: str, skip_validation: bool) -> Optional[Tuple[str, str]]:
        selector_list = self._deduplicate(selectors)
        if not selector_list:
            return None

        storage_state_path = self._session_store.storage_state_path(url)

        async with async_playwright() as p:
            browser, context, page = await _create_stealth_context(
                p, storage_state_path if self._session_store.has(url) else None
            )

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout)

                for selector in selector_list:
                    if skip_validation:
                        html = await self._fill_and_submit(page, handle, keyword)
                        await page.wait_for_timeout(self.post_submit_wait)
                        await context.storage_state(path=storage_state_path)
                        logger.success("Selector '%s' validated and submitted successfully", selector)
                        return selector, html
                    logger.info("Validating selector '%s'", selector)
                    handle = await self._get_valid_handle(page, selector)
                    if not handle:
                        logger.warning("Selector '%s' failed validation", selector)
                        continue
                    html = await self._fill_and_submit(page, handle, keyword)
                    await page.wait_for_timeout(self.post_submit_wait)
                    await context.storage_state(path=storage_state_path)
                    logger.success("Selector '%s' validated and submitted successfully", selector)
                    return selector, html
                
            finally:
                try:
                    await browser.close()
                except Exception:
                    logger.warning("Playwright browser failed to close cleanly")
        return None


    def _deduplicate(self, selectors: Iterable[str]) -> list[str]:
        seen = set()
        unique = []
        for selector in selectors:
            if not selector or selector in seen:
                continue
            seen.add(selector)
            unique.append(selector)
        return unique
    

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
        await page.wait_for_timeout(500)
        html = await page.content()
        return html