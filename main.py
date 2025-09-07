# main.py
import typer
from app.pipeline.graph import build_scraper_graph
from app.services.exporter import save_to_json, save_to_csv

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

    # Print parsed result
    print("===== FINAL RESULT =====")
    text = result.get("parsed_data")
    save_to_csv(text)
    save_to_json(text)

if __name__ == "__main__":
    app()
