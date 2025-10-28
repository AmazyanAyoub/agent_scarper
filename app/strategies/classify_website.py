import json
import os
import asyncio
from bs4 import BeautifulSoup
from collections import defaultdict
from app.services.fetcher import fetch_html
from app.core.config import DATA_FILE
from app.services.chains.builders import build_site_classifier_chain
from app.prompts.prompts import EXPANDED_CLASSIFIER_PROMPT


def load_examples():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_example(url: str, label: str, snippet: str):
    data = load_examples()
    if not any(entry["url"] == url for entry in data):
        data.append({"url": url, "label": label, "snippet": snippet})
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)


def select_examples(data, max_per_label=2):
    """Pick up to N examples per label, return as formatted string"""
    grouped = defaultdict(list)
    for entry in data:
        grouped[entry["label"]].append(entry)

    lines = []
    for label, entries in grouped.items():
        for e in entries[:max_per_label]:
            snippet_short = e["snippet"][:200].replace("\n", " ")
            lines.append(f"{e['url']} → {e['label']} | {snippet_short}...")
    return "\n".join(lines)


def build_hybrid_classifier(url: str) -> str:
    """
    Classify a website type using memory few-shot + LLM.
    """
    # 1. Check if already classified
    data = load_examples()
    for entry in data:
        if entry["url"] == url:
            return entry["label"]

    # 2. Fetch HTML
    html = asyncio.run(fetch_html(url))
    snippet = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)[:1000]

    # 3. Select balanced examples
    examples_str = select_examples(data)

    # 4. Prepare classifier chain
    classifier_chain = build_site_classifier_chain()

    # 5. Build prompt
    prompt = EXPANDED_CLASSIFIER_PROMPT.format(
        url=url,
        snippet=snippet,
        examples=examples_str if examples_str else "No examples yet."
    )

    # 6. Run classification
    result = classifier_chain.invoke(prompt)

    # 7. Save for future
    save_example(url, result, snippet[:500])

    return result
