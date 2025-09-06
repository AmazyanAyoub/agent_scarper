# main.py
import typer
from llm_scraper.pipeline.graph import build_scraper_graph

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
    print(result.get("parsed_data"))

if __name__ == "__main__":
    app()
