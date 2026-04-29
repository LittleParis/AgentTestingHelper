"""Compatibility helpers for LangGraph API drift across versions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from langgraph.types import Send
except ImportError:  # pragma: no cover - compatibility fallback
    from langgraph.constants import Send  # type: ignore


@dataclass(frozen=True)
class Overwrite:
    """Local overwrite wrapper handled by our reducer logic.

    Some LangGraph builds expose ``Overwrite`` from ``langgraph.types`` while
    others do not. We only need a lightweight signal that tells our reducer to
    replace the accumulated list instead of appending to it.
    """

    value: Any
