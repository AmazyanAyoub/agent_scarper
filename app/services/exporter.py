# exporter.py

import json 
import csv
from loguru import logger
from pathlib import Path
from typing import List, Dict

def export_results(ranked_links: List[Dict], output_dir: str = "outputs", formats: List[str] = ["json", "csv"]) -> None:
    """
    Export ranked results to JSON and/or CSV.
    Each entry = {"url": ..., "text": ..., "score": ...}
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    if "json" in formats:
        json_path = Path(output_dir) / "ranked_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(ranked_links, f, ensure_ascii=False, indent=2)
        logger.success(f"📄 Exported {len(ranked_links)} results to {json_path}")

    if "csv" in formats:
        csv_path = Path(output_dir) / "ranked_results.csv"
        with open(csv_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "text", "score"])
            writer.writeheader()
            for row in ranked_links:
                writer.writerow({
                    "url": row.get("url", ""),
                    "score": row.get("score", 0),
                    "text": row.get("text", "")  # truncate for readability
                })
        logger.success(f"📄 Exported {len(ranked_links)} results to {csv_path}")