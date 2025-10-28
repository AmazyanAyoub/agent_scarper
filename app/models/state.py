from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.cards import Cards


@dataclass
class AgentState:
    # Inputs
    url: str
    instruction: str

    # Classification
    site_type: Optional[str] = None

    # Ecommerce-specific context
    search_keyword: Optional[str] = None
    cards: List[Cards] = field(default_factory=list)
    selector_cache: Dict[str, Any] = field(default_factory=dict)

    # Diagnostics
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
