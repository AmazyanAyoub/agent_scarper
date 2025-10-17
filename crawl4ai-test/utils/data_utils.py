# utils/data_utils.py
import csv
from typing import Dict, Iterable, List

from models.Cards import Card  # Venue still available as alias

def _normalize_title(d: Dict) -> str:
    return (d.get("title") or d.get("name") or d.get("product_name") or d.get("heading") or "").strip()

def is_duplicate_venue(venue_key: str, seen_keys: set) -> bool:
    return venue_key in seen_keys

def is_complete_venue(item: Dict, required_keys: List[str]) -> bool:
    """
    Accepts aliases so REQUIRED_KEYS stay portable across sites.
    """
    alias_map = {
        "title": ["title", "name", "product_name", "heading"],
        "url": ["url", "link", "href"],
        "image_url": ["image_url", "image", "img"],
        "price": ["price", "amount"],
        "reviews": ["reviews", "reviews_count"],
        "location": ["location", "city", "place"],
    }
    for key in required_keys or []:
        if key in item and item[key] not in (None, ""):
            continue
        if any(a in item and item[a] not in (None, "") for a in alias_map.get(key, [])):
            continue
        return False
    return True

def _collect_headers(rows: Iterable[Dict]) -> List[str]:
    seen = set()
    base = list(Card.model_fields.keys())  # start with schema order
    for k in base:
        seen.add(k)
    extras = []
    for r in rows:
        for k in r.keys():
            if k not in seen:
                extras.append(k)
                seen.add(k)
    return base + extras

def save_venues_to_csv(items: List[Dict], filename: str):
    if not items:
        print("No cards to save.")
        return
    fieldnames = _collect_headers(items)
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in items:
            writer.writerow(row)
    print(f"Saved {len(items)} cards to '{filename}'.")
