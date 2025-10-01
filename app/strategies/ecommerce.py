"""High-level orchestration for ecommerce sites.

This module assumes the calling code already:
    1. Classified the target site as ecommerce.
    2. Warmed up Playwright with captcha/session handling.

The ecommerce flow coordinates selector detection, verification, and
search execution so we can pivot to result parsing afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger
from urllib.parse import urlparse
from app.services.fetcher import fetch_html
from app.services.parser import detect_search_selector, detect_search_selector_llm
from app.services.selector_validator import SelectorValidator
from app.services.search_intent import build_search_intent
from app.services.selector_store import SelectorStore


DEFAULT_TEST_KEYWORD = "test"


@dataclass
class EcommerceContext:
    url: str
    instruction: str
    html: Optional[str] = None
    selector_candidates: list[str] = None
    validated_selector: Optional[str] = None
    result_html: Optional[str] = None


class EcommerceStrategy:
    """Coordinates the ecommerce-specific scraping steps."""

    def __init__(self, validator: SelectorValidator | None = None, selector_store: SelectorStore | None = None):
        self.validator = validator or SelectorValidator()
        self.selector_store = selector_store or SelectorStore()

    async def run(self, url: str, instruction: str) -> EcommerceContext:
        ctx = EcommerceContext(url=url, instruction=instruction)

        search_intent = build_search_intent(ctx.instruction)
        keyword = search_intent.keyword
        domain = self._domain(url)
        cached_selector = self.selector_store.get(domain)
        if cached_selector:
            logger.info("Using cached selector '%s' for %s", cached_selector, domain)
            result = await self.validator.validate_and_submit(
                url=url,
                selectors=[cached_selector],
                keyword=keyword,
                skip_validation=True,
            )
            if result:
                ctx.validated_selector, ctx.result_html = result
                return ctx
            logger.warning("Cached selector '%s' failed; falling back to detection", cached_selector)

        ctx.html = await fetch_html(url, wait=5000, timeout=60000)
        if not ctx.html:
            logger.error("Failed to fetch HTML for %s", url)
            return ctx
        
        ctx.selector_candidates = self._collect_candidates(ctx.html)
        if not ctx.selector_candidates:
            logger.error("No selector candidates produced for %s", url)
            return ctx
        
        result = await self.validator.validate_and_submit(
            url=url,
            selectors=ctx.selector_candidates,
            keyword=keyword,
            skip_validation=False,
        )
        if result:
            ctx.validated_selector, ctx.result_html = result
            self.selector_store.set(domain, ctx.validated_selector)
        else:
            logger.error("No valid search input selector found for %s", url)

        return ctx

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def _collect_candidates(self, html: str) -> list[str]:
        selectors: list[str] = []

        primary = detect_search_selector(html)
        if primary and primary.upper() != "NONE":
            selectors.append(primary)

        try:
            llm_selector = detect_search_selector_llm(html)
        except Exception as exc:
            logger.warning("LLM selector detection failed: %s", exc)
        else:
            if llm_selector and llm_selector.upper() != "NONE":
                selectors.append(llm_selector)
        # Deduplicate while preserving order
        seen = set()
        unique_selectors = []
        for selector in selectors:
            if selector not in seen:
                seen.add(selector)
                unique_selectors.append(selector)

        logger.info("Selector candidates: %s", unique_selectors)
        return unique_selectors


async def run_ecommerce_flow(url: str, instruction: str) -> EcommerceContext:
    strategy = EcommerceStrategy()
    return await strategy.run(url, instruction)
