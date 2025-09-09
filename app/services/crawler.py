
from loguru import logger
from app.services.fetcher import fetch_html_links
from app.services.cleaner import extract_main_content

async def crawl_site_step(frontier: list, visited: set, wait: int = 3000):
    """
    Crawl one depth level only (the given frontier).
    Returns:
        - candidate_pages found at this level
        - updated visited set
        - new frontier for the next step
    """
    candidate_pages = []
    new_frontier = []

    for url in frontier:
        if url in visited:
            continue

        visited.add(url)

        html, links = await fetch_html_links(url, wait)
        if not html:
            continue

        text = extract_main_content(html)
        if text:
            candidate_pages.append({"url": url, "text": text})

        for link in links:
            if link["url"] not in visited:
                new_frontier.append(link["url"])

    return candidate_pages, visited, new_frontier



