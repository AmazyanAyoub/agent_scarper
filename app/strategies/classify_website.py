import json
import os
import asyncio
from bs4 import BeautifulSoup
from collections import defaultdict
from app.services.fetcher import fetch_html
from app.core.config import DATA_FILE
from app.services.chains.builders import build_site_classifier_chain
from app.prompts.prompts import EXPANDED_CLASSIFIER_PROMPT


_examples_cache = None
_label_cache = None  # url -> label

def load_examples():
    global _examples_cache, _label_cache
    if _examples_cache is not None:
        return _examples_cache

    if not os.path.exists(DATA_FILE):
        _examples_cache, _label_cache = [], {}
        return _examples_cache

    with open(DATA_FILE, "r") as f:
        _examples_cache = json.load(f)
    _label_cache = {e["url"]: e["label"] for e in _examples_cache}
    return _examples_cache


def save_example(url: str, label: str, snippet: str):
    global _label_cache
    data = load_examples()

    if _label_cache and url in _label_cache:
        return

    entry = {"url": url, "label": label, "snippet": snippet}
    data.append(entry)

    if _label_cache is not None:
        _label_cache[url] = label

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def select_examples(data, max_per_label=2, max_total=30):
    """Pick up to N examples per label, but also cap global total."""
    grouped = defaultdict(list)
    for entry in data:
        bucket = grouped[entry["label"]]
        if len(bucket) < max_per_label:
            bucket.append(entry)

    lines = []
    count = 0
    for label, entries in grouped.items():
        for e in entries:
            if count >= max_total:
                break
            snippet_short = e["snippet"][:160].replace("\n", " ")
            lines.append(f"{e['url']} → {e['label']} | {snippet_short}...")
            count += 1
    return "\n".join(lines)


def build_hybrid_classifier(url: str) -> str:
    """
    Classify a website type using memory few-shot + LLM.
    """
    data = load_examples()

    label = _label_cache.get(url) if _label_cache else None
    if label is not None:
        return label

    # 2. Fetch HTML
    html = asyncio.run(fetch_html(url))
    snippet = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)[:1000]

    # 3. Select balanced examples
    examples_str = select_examples(data)

    # 4. Prepare classifier chain
    classifier_chain = build_site_classifier_chain(url, snippet, examples_str)
    
    # # 6. Run classification
    result = classifier_chain.invoke()

    # 7. Save for future
    save_example(url, result, snippet[:500])

    return result
