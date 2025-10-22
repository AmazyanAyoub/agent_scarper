"""Asynchronous product-card enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from loguru import logger

from app.models.cards import Cards
from app.services.fetcher import fetch_html


@dataclass
class CardEnricher:
    wait_ms: int = 4000
    timeout_ms: Optional[int] = 45000

    async def enrich(self, card: Cards, base_url: Optional[str] = None) -> Cards:
        if not card.url:
            logger.debug("Card has no URL; skipping enrichment.")
            return card

        absolute_url = urljoin(base_url or "", card.url)
        html = await fetch_html(absolute_url, wait=self.wait_ms, timeout=self.timeout_ms)

        if not html:
            logger.warning("Could not fetch detail page for %s", absolute_url)
            return card

        soup = BeautifulSoup(html, "lxml")
        enriched = card.model_copy(update=self._extract_fields(card, soup, absolute_url))
        return enriched

    def _extract_fields(self, card: Cards, soup: BeautifulSoup, url: str) -> dict:
        updates: dict[str, Optional[str]] = {}

        if h1 := soup.select_one("h1"):
            title = h1.get_text(" ", strip=True)
            updates["title"] = title or card.title
            updates["name"] = title or card.name

        price_el = soup.select_one("[id*='priceblock'], [class*='price']")
        price_text = price_el.get_text(" ", strip=True) if price_el else None
        if price_text:
            updates["price"] = price_text

        availability_el = soup.select_one("[id*='availability'], [class*='availability']")
        if availability_el:
            updates["availability"] = availability_el.get_text(" ", strip=True)

        seller_el = soup.select_one("[id*='sellerProfileTriggerId'], [class*='seller']")
        if seller_el:
            updates["seller"] = seller_el.get_text(" ", strip=True)

        rating_el = soup.select_one("[class*='rating']")
        if rating_el:
            try:
                updates["rating"] = float(rating_el.get_text(" ", strip=True).split()[0])
            except ValueError:
                pass

        bullets = [li.get_text(" ", strip=True) for li in soup.select("ul li") if li.get_text(strip=True)]
        if bullets:
            specs = dict(card.specs or {})
            specs["detail_bullets"] = bullets[:10]
            updates["specs"] = specs

        image_el = soup.select_one("img[data-old-hires], img[srcset], img[src]")
        if image_el:
            for attr in ("data-old-hires", "srcset", "src"):
                val = image_el.get(attr)
                if val:
                    updates["image_url"] = val.split()[0]
                    break

        updates["url"] = url  # store absolute URL
        return updates

card_enricher = CardEnricher()
