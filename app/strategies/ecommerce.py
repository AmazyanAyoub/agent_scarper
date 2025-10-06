"""High-level orchestration for ecommerce sites.

This module assumes the calling code already:
    1. Classified the target site as ecommerce.
    2. Warmed up Playwright with captcha/session handling.

The ecommerce flow coordinates selector detection, verification, and
search execution so we can pivot to result parsing afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger
from urllib.parse import urlparse
from app.services.fetcher import fetch_html
from app.services.parser import detect_search_selectors
from app.services.selector_validator import SelectorValidator
from app.services.search_intent import build_search_intent
from app.services.selector_store import SelectorStore
from app.services.html_filtering import extract_products, save_products, ProductEntry


DEFAULT_TEST_KEYWORD = "test"


@dataclass
class EcommerceContext:
    url: str
    instruction: str
    html: Optional[str] = None
    selector_candidates: list[str] = None
    validated_selector: Optional[str] = None
    result_html: Optional[str] = None
    search_keyword: str = None
    products: list[ProductEntry] | None = None
    output_path: str | None = None


class EcommerceStrategy:
    """Coordinates the ecommerce-specific scraping steps."""

    def __init__(self, validator: SelectorValidator | None = None, selector_store: SelectorStore | None = None):
        self.validator = validator or SelectorValidator()
        self.selector_store = selector_store or SelectorStore()

    async def run(self, url: str, instruction: str) -> EcommerceContext:
        ctx = EcommerceContext(url=url, instruction=instruction)
        
        keyword_parts: list[str] = []
        search_intent = build_search_intent(ctx.instruction)
        
        if search_intent.keyword and search_intent.keyword.lower() != "udgu":
            keyword_parts.append(search_intent.keyword.strip())
        else:
            logger.warning("No Keyword found")
        for condition in search_intent.conditions:
            if isinstance(condition, str):
                keyword_parts.append(condition.strip())
                continue
            if condition.apply_via == "keyword" and condition.value:
                keyword_parts.append(condition.value.strip())

        ctx.search_keyword = " ".join(part for part in keyword_parts if part)
        domain = self._domain(url)
        cached_selector = self.selector_store.get(domain)
        if cached_selector:
            logger.info("Using cached selector '%s' for %s", cached_selector, domain)
            result = await self.validator.validate_and_submit(
                url=url,
                selectors=[cached_selector],
                keyword=ctx.search_keyword,
                skip_validation=True,
            )
            if result:
                ctx.validated_selector, ctx.result_html = result
                products = extract_products(ctx.result_html, base_url=url, limit=20)
                ctx.products = products
                ctx.selector_candidates = [cached_selector]
                if products:
                    filename = f"app/data/products/{self._domain(url)}.json"
                    save_products(products, filename)
                    ctx.output_path = filename
                return ctx
            logger.warning("Cached selector '%s' failed; falling back to detection", cached_selector)

        ctx.html = await fetch_html(url, wait=5000, timeout=60000)
        if not ctx.html:
            logger.error("Failed to fetch HTML for %s", url)
            return ctx
        
        ctx.selector_candidates = detect_search_selectors(ctx.html, limit=10)
        if not ctx.selector_candidates:
            logger.error("No selector candidates produced for %s", url)
            return ctx
        
        result = await self.validator.validate_and_submit(
            url=url,
            selectors=ctx.selector_candidates,
            keyword=ctx.search_keyword,
            skip_validation=False,
        )
        if result:
            ctx.validated_selector, ctx.result_html = result
            products = extract_products(ctx.result_html, base_url=url, limit=20)
            self.selector_store.set(domain, ctx.validated_selector)
            ctx.products = products
            if products:
                filename = f"app/data/products/{self._domain(url)}.json"
                save_products(products, filename)
        else:
            logger.error("No valid search input selector found for %s", url)
        return ctx

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()


async def run_ecommerce_flow(url: str, instruction: str) -> EcommerceContext:
    strategy = EcommerceStrategy()
    return await strategy.run(url, instruction)
