# test_pipeline.py

import json
from app.pipeline.graph import build_scraper_graph

def main():
    instruction = "Find articles about reinforcement learning for robotics"

    state = {
        "url": "https://blogs.nvidia.com/",
        "instruction": instruction,
        "depth": 0,
        "frontier": [{"url": "https://blogs.nvidia.com/", "text": ""}],
        "visited_links": set(),
        "visited_html": set(),
        "verified_links": [],
        "batch_index": 0
    }

    graph = build_scraper_graph(target_results=5, top_k=3, MAX_DEPTH=2)

    response = graph.invoke(state,{"recursion_limit": 100})


    def make_serializable(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj
    with open("outputs/results.json", "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2, ensure_ascii=False, default=make_serializable)

if __name__ == "__main__":
    main()