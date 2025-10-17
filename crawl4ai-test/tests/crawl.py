# scrape_raw.py
import asyncio
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

TARGET_URL = (
    "https://www.ebay.com/sch/i.html?_nkw=iphone+15&_ipg=120"
)

def build_browser_config() -> BrowserConfig:
    return BrowserConfig(
        browser_type="chromium",
        headless=False,
        enable_stealth=True,
        use_persistent_context=True,
        user_data_dir=str(Path("debug") / ".user-data"),
        viewport_width=1366,
        viewport_height=768,
        ignore_https_errors=True,
        extra_args=["--disable-blink-features=AutomationControlled"],
    )

async def grab_raw_page() -> None:
    debug_dir = Path("debug")
    debug_dir.mkdir(exist_ok=True)

    async with AsyncWebCrawler(config=build_browser_config()) as crawler:
        result = await crawler.arun(
            url=TARGET_URL,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                session_id="raw_dump",
                wait_until="networkidle",
                wait_for="ul.srp-results, li.s-item",
                wait_for_timeout=20000,
                scan_full_page=True,
                scroll_delay=0.2,
                mean_delay=0.5,
                max_range=1.2,
                simulate_user=True,
                remove_overlay_elements=True,
                magic=True,
                js_code=[
                    "(()=>{document.querySelector('#gdpr-banner-accept,button#gdpr-banner-accept,button[aria-label*\"Accept\"]').click?.()})()",
                ],
                screenshot=True,
                log_console=True,
            ),
        )

    raw_path = debug_dir / "cards_raw.html"
    raw_path.write_text(result.html or "", encoding="utf-8")
    print(f"Saved raw HTML to {raw_path}")

if __name__ == "__main__":
    asyncio.run(grab_raw_page())
