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

    def get(self, domain: str) -> Optional[str]:
        return self._load().get(domain)

    def set(self, domain: str, selector: str) -> None:
        data = self._load()
        data[domain] = selector
        self._dump(data)
