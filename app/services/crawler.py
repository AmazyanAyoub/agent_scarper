
from loguru import logger
from app.services.fetcher import fetch_html, fetch_links
from app.services.cleaner import extract_main_content


async def crawl_links(frontier: list, visited_links: set, wait: int = 3000):
    """
    Crawl one depth level only (the given frontier).
    Returns:
        - updated visited set
        - new frontier for the next step
    """  
    new_frontier = []

    for front in frontier:
        if isinstance(front, str):
            url = front
        else:
            url = front.get("url")

        if not url or url in visited_links:
            continue

        visited_links.add(url)

        html = await fetch_html(url)
        links = fetch_links(html, url)

        for link in links:
            if link["url"] not in visited_links:
                new_frontier.append(link)
    
    return new_frontier, visited_links

async def crawl_html(frontier: list, visited_html: set, wait: int = 3000):
    """
    Crawl one depth level only (the given frontier).
    Returns:
        - candidate_pages found at this level
        - updated visited set
        - new frontier for the next step
    """
    candidate_pages = []

    for link in frontier:
        url = link["url"]  # frontier now contains dicts {url, text}

        if url in visited_html:
            continue

        visited_html.add(url)

        html = await fetch_html(url, wait)
        if not html:
            continue

        text = extract_main_content(html)
        if text:
            candidate_pages.append({"url": url, "text": text})

    return candidate_pages, visited_html, html



