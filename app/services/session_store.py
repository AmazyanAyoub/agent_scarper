import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, Optional, Union

StoragePayload = Union[str, Path, Dict[str, Any]]


class SessionStore:
    def __init__(self, base_dir: Path | str = Path("app/data/sessions")):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def _path(self, url: str) -> Path:
        return self.base_dir / f"{self._domain(url)}.json"

    def storage_state_path(self, url: str) -> str:
        """Location on disk where Playwright-compatible storage_state is stored."""
        path = self._path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def has(self, url: str) -> bool:
        return self._path(url).exists()

    def save(self, url: str, state: Dict[str, Any]) -> None:
        path = self._path(url)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def import_storage_state(self, url: str, payload: StoragePayload) -> None:
        """Normalise an external storage_state (dict, json string, or file) into the store."""
        if isinstance(payload, (str, Path)):
            payload_path = Path(payload)
            if payload_path.exists():
                data = json.loads(payload_path.read_text(encoding="utf-8"))
            else:
                data = json.loads(str(payload))
        else:
            data = payload
        self.save(url, data)