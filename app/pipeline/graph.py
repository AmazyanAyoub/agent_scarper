from __future__ import annotations

import asyncio
from typing import Literal

from langgraph.graph import END, StateGraph

from app.core.logger import get_logger
from app.models.state import AgentState
from app.strategies.classify_website import build_hybrid_classifier
from app.strategies.ecommerce import run_ecommerce_flow

logger = get_logger(__name__)
