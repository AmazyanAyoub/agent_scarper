import json
from pathlib import Path
from typing import Optional
from app.core.config import DEFAULT_SELECTOR_CACHE_PATH




class SelectorStore:
    def __init__(self, path: Path | str = DEFAULT_SELECTOR_CACHE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _dump(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
    def get(self, domain: str) -> dict:
        return self._load().get(domain) or {}

    def set(self, domain: str, payload: dict) -> None:
        data = self._load()
        existing = data.get(domain) or {}
        existing.update(payload)
        data[domain] = existing
        self._dump(data)
