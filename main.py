# main.py
import typer
from app.pipeline.graph import build_scraper_graph
from app.services.exporter import export_results

app = typer.Typer()

@app.command()
def run(
    url: str = typer.Option(..., "--url", help="The URL to scrape"),
    instruction: str = typer.Option(..., "--instruction", help="Instruction for the scraper"),
    # use_playwright: bool = typer.Option(False, "--use-playwright", help="Use Playwright instead of httpx"),
):
    graph = build_scraper_graph()

    # Input state for LangGraph
    state = {
        "url": url,
        "instruction": instruction,
    }

    # Run graph
    result = graph.invoke(state)

if __name__ == "__main__":
    app()
