# cli.py

import asyncio

import typer
from loguru import logger
from llm_scraper.utils.fetcher import fetch_html_playwright, fetch_with_httpx
from llm_scraper.utils.cleaner import extract_main_content, chunk_html
from llm_scraper.prompts.templates import get_extraction_prompt

app = typer.Typer()

@app.command()
def run(
    url: str = typer.Option(..., "--url", help="The URL to scrape"),
    instruction: str = typer.Option(..., "--instruction", help="Instruction for the scraper"),
    use_playwright: bool = typer.Option(False, "--use-playwright", help="Use Playwright instead of httpx"),
):
    """
    Run the scraper with a given URL and user instruction.
    Example:
        python main.py run --url "https://quotes.toscrape.com/js/" --instruction "extract all quotes"
    """

    logger.info(f"Runing the scraper with the given url : {url}")
    
    html = (
        asyncio.run(fetch_html_playwright(url))
        if use_playwright
        else fetch_with_httpx(url)
    )

    if not html:
        logger.error("failed to fetch HTML")
        raise typer.Exit(1)
    
    text = extract_main_content(html)
    chunks = chunk_html(text)

    prompt = get_extraction_prompt(instruction, chunks)
    logger.info("Prompt built successfully.")

    typer.echo("===== FINAL PROMPT =====")
    typer.echo(prompt)