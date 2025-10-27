"""High-level orchestration for ecommerce sites using Playwright + heuristics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from loguru import logger

from app.models.cards import Cards
from app.services.fetcher import fetch_html
from app.services.parser import detect_search_selectors
from app.services.search_intent import build_search_intent
from app.services.selector_store import SelectorStore
from app.services.selector_validator import SelectorValidator
from app.services.session_store import SessionStore
# from app.services.html_filtering import extract_cards  # <- heuristic extractor
# from app.services.card_enricher import card_enricher
from app.services.card_selector import extract_cards_from_html

DEFAULT_TEST_KEYWORD = "test"


@dataclass
class EcommerceContext:
    url: str
    instruction: str
    html: Optional[str] = None
    selector_candidates: Optional[list[str]] = None
    validated_selector: Optional[str] = None
    result_html: Optional[str] = None
    search_keyword: Optional[str] = None
    products: Optional[list[Cards]] = None
    output_path: Optional[str] = None


class EcommerceStrategy:
    """Coordinates the ecommerce-specific scraping steps."""

    def __init__(
        self,
        validator: SelectorValidator | None = None,
        selector_store: SelectorStore | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        self.validator = validator or SelectorValidator()
        self.selector_store = selector_store or SelectorStore()
        self.session_store = session_store or SessionStore()

    async def run(self, url: str, instruction: str) -> EcommerceContext:
        ctx = EcommerceContext(url=url, instruction=instruction)

        ctx.search_keyword = self._build_search_keyword(instruction)
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

                await self._populate_cards(ctx, domain)
                ctx.selector_candidates = [cached_selector]
                return ctx
            logger.warning(
                "Cached selector '%s' failed; falling back to detection",
                cached_selector,
            )

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
            await self._populate_cards(ctx, domain)
            if ctx.validated_selector:
                self.selector_store.set(domain, ctx.validated_selector)
        else:
            logger.error("No valid search input selector found for %s", url)

        return ctx

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def _build_search_keyword(self, instruction: str) -> str:
        keyword_parts: list[str] = []
        search_intent = build_search_intent(instruction)

        if search_intent.keyword and search_intent.keyword.lower() != "udgu":
            keyword_parts.append(search_intent.keyword.strip())
        else:
            logger.warning("No keyword found in instruction")

        for condition in search_intent.conditions:
            if isinstance(condition, str):
                keyword_parts.append(condition.strip())
                continue
            if condition.apply_via == "keyword" and condition.value:
                keyword_parts.append(condition.value.strip())

        return " ".join(part for part in keyword_parts if part) or DEFAULT_TEST_KEYWORD

    async def _populate_cards(self, ctx: EcommerceContext, domain: str) -> None:
        if not ctx.result_html:
            logger.warning("No result HTML available to process for %s", ctx.url)

            return

        extraction = extract_cards_from_html(
            ctx.result_html,
            base_url=ctx.url,
            limit=10,
        )
        ctx.products = extraction.cards or []

        if ctx.products:
            ctx.output_path = self._save_cards(domain, ctx.products)
            # await self._enrich_cards(ctx.products, ctx.url, domain)
        else:
            ctx.output_path = None

    def _save_cards(self, domain: str, cards: list[Cards]) -> str:
        output_dir = Path("app/data/products")
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{domain}.json"
        payload = [card.model_dump() for card in cards]
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Persisted %d cards to %s", len(cards), file_path)
        return str(file_path)

    # async def _enrich_cards(self, cards: list[Cards], base_url: str, domain: str) -> None:
    #     enriched: list[Cards] = []
    #     for card in cards:
    #         enriched_card = await card_enricher.enrich(card, base_url)
    #         enriched.append(enriched_card)

    #     output_dir = Path("app/data/products")
    #     output_dir.mkdir(parents=True, exist_ok=True)
    #     file_path = output_dir / f"{domain}_enriched.json"
    #     file_path.write_text(
    #         json.dumps([card.model_dump() for card in enriched], ensure_ascii=False, indent=2),
    #         encoding="utf-8",
    #     )
    #     logger.info("Enriched %d cards to %s", len(enriched), file_path)


async def run_ecommerce_flow(url: str, instruction: str) -> EcommerceContext:
    strategy = EcommerceStrategy()
    return await strategy.run(url, instruction)
