
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from dotenv import load_dotenv
from loguru import logger
from pydantic import ValidationError

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMConfig,
    LLMExtractionStrategy,
    ProxyConfig,
    RoundRobinProxyStrategy,
    browser_manager
)

from app.core.config import DEFAULT_MODEL, DEFAULT_PROVIDER, PRODUCT_CONTAINER_TAGS
from app.models.cards import Cards
from app.prompts.prompts import CARD_PROMPT

load_dotenv()


@dataclass
class Crawl4AIResult:
    cards: List[Cards]
    html: str
    markdown: Optional[str]
    raw_extraction: Optional[object]


class Crawl4AIAdapter:
    """Orchestrates crawl4ai to extract ecommerce cards."""

    def __init__(
        self,
        *,
        session_dir: str = "app/data/crawl4ai_sessions",
        headless: bool = True,
        enable_stealth: bool = False,
        default_wait_for: Optional[str] = None,
        default_target_elements: Optional[Sequence[str]] = None,
        # proxy_pool: Optional[Sequence[str]] = None,
        verbose: bool = False,
    ) -> None:
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.enable_stealth = enable_stealth
        self.default_wait_for = default_wait_for
        self.default_target_elements = tuple(default_target_elements or PRODUCT_CONTAINER_TAGS)
        self.verbose = verbose
        # self.proxy_strings = tuple(proxy_pool or self._read_proxies_from_env())

    async def extract_cards(
        self,
        url: str,
        *,
        session_id: str,
        storage_state_path: Optional[str] = None,
        html: Optional[str] = None,
        wait_for: Optional[str] = None,
        target_elements: Optional[Sequence[str]] = None,
        headers: Optional[dict] = None,
        cookies: Optional[Iterable[dict]] = None,
    ) -> Crawl4AIResult:
        strategy = self._build_llm_strategy()
        run_config = self._build_run_config(
            session_id=session_id,
            strategy=strategy,
            wait_for=wait_for,
            target_elements=target_elements,
        )
        browser_config = self._build_browser_config(
            session_key=session_id,
            storage_state_path=storage_state_path,
            headers=headers,
            cookies=list(cookies or ()),
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # if html:
            #     result = await crawler.arun(url=url, html=html, config=run_config)
            # else:
            result = await crawler.arun(url=url, config=run_config)

        return self._build_result(result)

    def _build_browser_config(
        self,
        *,
        session_key: str,
        storage_state_path: Optional[str],
        headers: Optional[dict],
        cookies: List[dict],
    ) -> BrowserConfig:
        profile_dir = self.session_dir / "profiles" / session_key
        profile_dir.mkdir(parents=True, exist_ok=True)
        # proxy = self._proxy_config()
        return BrowserConfig(
            browser_type="chromium",
            channel="chrome",
            headless=self.headless,
            enable_stealth=self.enable_stealth,
            use_persistent_context=True,
            user_data_dir=str(profile_dir),
            storage_state=storage_state_path,
            # proxy_config=proxy,
            headers=headers or {},
            cookies=cookies,
            ignore_https_errors=True,
            verbose=self.verbose,
        )

    def _build_run_config(
        self,
        *,
        session_id: str,
        strategy: LLMExtractionStrategy,
        wait_for: Optional[str],
        target_elements: Optional[Sequence[str]],
    ) -> CrawlerRunConfig:
        # rotation = self._proxy_rotation_strategy()
        selectors = list(target_elements) if target_elements else list(self.default_target_elements)
        selectors = selectors or None
        return CrawlerRunConfig(
            extraction_strategy=strategy,
            cache_mode=CacheMode.ENABLED,
            session_id=session_id,
            wait_until="domcontentloaded",
            wait_for=wait_for or self.default_wait_for,
            wait_for_timeout=45000 if (wait_for or self.default_wait_for) else None,
            scan_full_page=True,
            process_iframes=False,
            delay_before_return_html=0.3,
            # proxy_rotation_strategy=rotation,
            target_elements=selectors,
        )

    def _build_llm_strategy(self) -> LLMExtractionStrategy:
        provider = f"{DEFAULT_PROVIDER}/{DEFAULT_MODEL}"
        llm_config = LLMConfig(provider=provider, api_token=os.getenv("GROQ_API_KEY"))
        return LLMExtractionStrategy(
            llm_config=llm_config,
            schema=Cards.model_json_schema(),
            extraction_type="schema",
            instruction=CARD_PROMPT,
            input_format="markdown",
            verbose=self.verbose,
        )

    def _build_result(self, crawl_result) -> Crawl4AIResult:
        if not getattr(crawl_result, "success", False):
            logger.warning("crawl4ai run failed for %s", getattr(crawl_result, "url", ""))
        raw = crawl_result.extracted_content
        parsed = self._parse_extracted_content(raw)
        cards = self._build_cards(parsed)
        markdown = None
        try:
            markdown_result = crawl_result.markdown
            markdown = getattr(markdown_result, "raw_markdown", None)
        except AttributeError:
            markdown = None
        return Crawl4AIResult(
            cards=cards,
            html=crawl_result.html or "",
            markdown=markdown,
            raw_extraction=parsed,
        )

    # def _build_cards(self, payload: Optional[object]) -> List[Cards]:
    #     cards: List[Cards] = []
    #     if not payload:
    #         return cards
    #     candidates = self._flatten_payload(payload)
    #     seen = set()
    #     for item in candidates:
    #         if not isinstance(item, dict):
    #             continue
    #         card = self._coerce_card(item)
    #         if not card:
    #             continue
    #         fingerprint = self._dedupe_key(card)
    #         if fingerprint in seen:
    #             continue
    #         seen.add(fingerprint)
    #         cards.append(card)
    #     return cards

    def _build_cards(self, payload: Optional[object]) -> List[Cards]:
        cards: List[Cards] = []
        if not payload:
            return cards

        candidates = self._flatten_payload(payload)
        seen = set()

        for item in candidates:
            if not isinstance(item, dict):
                continue
            card = self._coerce_card(item)
            if not card:
                continue

            fingerprint = self._dedupe_key(card)
            if fingerprint in seen:
                continue

            seen.add(fingerprint)
            cards.append(card)
            if len(cards) >= 10:      # ← keep only the first 10
                break

        return cards

    def _coerce_card(self, payload: dict) -> Optional[Cards]:
        normalized = {}
        for field in Cards.model_fields:
            value = payload.get(field)
            if value is None:
                value = ""
            if not isinstance(value, str):
                value = str(value)
            normalized[field] = value.strip()
        try:
            return Cards(**normalized)
        except ValidationError:
            return None

    @staticmethod
    def _dedupe_key(card: Cards) -> tuple[str, str, str]:
        return (
            card.name.lower(),
            card.location.lower(),
            card.price.lower(),
        )

    def _parse_extracted_content(self, extracted: Optional[str]) -> Optional[object]:
        if not extracted:
            return None
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            logger.debug("Failed to decode crawl4ai extraction as JSON")
            return extracted

    @staticmethod
    def _flatten_payload(payload: object) -> List[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "items", "results", "cards"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return [payload]
        return []

    # def _proxy_config(self) -> Optional[ProxyConfig]:
    #     proxies = self._materialize_proxies()
    #     return proxies[0] if proxies else None

    # def _proxy_rotation_strategy(self) -> Optional[RoundRobinProxyStrategy]:
    #     proxies = self._materialize_proxies()
    #     if not proxies:
    #         return None
    #     return RoundRobinProxyStrategy(list(proxies))

    # def _materialize_proxies(self) -> List[ProxyConfig]:
    #     configs: List[ProxyConfig] = []
    #     for raw in self.proxy_strings:
    #         try:
    #             configs.append(ProxyConfig.from_string(raw))
    #         except Exception as exc:  # noqa: BLE001
    #             logger.debug("Skipping proxy '%s' due to %s", raw, exc)
    #     return configs

    # @staticmethod
    # def _read_proxies_from_env() -> List[str]:
    #     raw = os.getenv("CRAWL4AI_PROXIES") or os.getenv("PROXIES") or ""
    #     return [item.strip() for item in raw.split(',') if item.strip()]

