# # main.py
# import asyncio
# from crawl4ai import AsyncWebCrawler
# from dotenv import load_dotenv

# from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS
# from utils.data_utils import save_venues_to_csv
# from utils.scraper_utils import (
#     fetch_and_process_page,
#     get_browser_config,
#     get_llm_strategy,
# )

# load_dotenv()

# async def crawl_venues():
#     """
#     Crawl generic 'cards' (phones, venues, etc.) from a website.
#     """
#     browser_config = get_browser_config()
#     llm_strategy = get_llm_strategy()
#     session_id = "cards_crawl_session"

#     page_number = 1
#     all_items = []
#     seen_names = set()

#     async with AsyncWebCrawler(config=browser_config) as crawler:
#         while True and page_number < 2:  # keep it small while testing
#             items, no_results_found = await fetch_and_process_page(
#                 crawler,
#                 page_number,
#                 BASE_URL,
#                 CSS_SELECTOR,
#                 llm_strategy,
#                 session_id,
#                 REQUIRED_KEYS,
#                 seen_names,
#             )

#             if no_results_found:
#                 print("No more cards found. Ending crawl.")
#                 break

#             if not items:
#                 print(f"No cards extracted from page {page_number}.")
#                 break

#             all_items.extend(items)
#             page_number += 1
#             await asyncio.sleep(2)

#     if all_items:
#         save_venues_to_csv(all_items, "cards.csv")
#         print(f"Saved {len(all_items)} cards to 'cards.csv'.")
#     else:
#         print("No cards were found during the crawl.")

#     llm_strategy.show_usage()

# async def main():
#     await crawl_venues()

# if __name__ == "__main__":
#     asyncio.run(main())


# main.py
import asyncio
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

# config
from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS

# scraping / parsing helpers (LLM not used)
from utils.scraper_utils import (
    get_browser_config,
    fetch_and_process_page,   # deterministic (BeautifulSoup) version
)

# output helpers
from utils.data_utils import save_venues_to_csv


async def crawl_cards(max_pages: int = 3, delay_seconds: float = 1.5) -> None:
    """
    Crawl generic listing 'cards' (phones, venues, etc.) deterministically (no LLM),
    auto-detecting the card selector when CSS_SELECTOR == "AUTO".
    Saves results to cards.csv
    """
    load_dotenv()

    browser_config = get_browser_config()
    session_id = "cards_crawl_session"

    all_items = []
    seen_keys = set()
    page_number = 1

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while page_number <= max_pages:
            items, _ = await fetch_and_process_page(
                crawler=crawler,
                page_number=page_number,
                base_url=BASE_URL,
                css_selector=CSS_SELECTOR,   # "AUTO" -> auto-pick inside scraper_utils
                session_id=session_id,
                required_keys=REQUIRED_KEYS, # e.g., ["title","url"]
                seen_names=seen_keys,
            )

            if not items:
                print(f"No cards extracted from page {page_number}. Stopping.")
                break

            all_items.extend(items)
            print(f"Total so far: {len(all_items)}")
            page_number += 1
            await asyncio.sleep(delay_seconds)

    if all_items:
        save_venues_to_csv(all_items, "cards.csv")
        print(f"Saved {len(all_items)} cards to 'cards.csv'.")
    else:
        print("No cards were found during the crawl.")


async def main():
    await crawl_cards(max_pages=1, delay_seconds=1.25)  # tweak pages & pacing as needed


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
