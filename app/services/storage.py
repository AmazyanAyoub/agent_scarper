from app.models.cards import Cards
from loguru import logger
from pathlib import Path
import json

def save_cards(self, domain: str, cards: list[Cards]) -> str:
    output_dir = Path("app/data/products")
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{domain}.json"
    payload = [card.model_dump() for card in cards]
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Persisted %d cards to %s", len(cards), file_path)
    return str(file_path)