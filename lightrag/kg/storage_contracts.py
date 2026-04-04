from __future__ import annotations

from typing import Any


def resolve_storage_workspace(*candidates: Any, default: str = "default") -> str:
    """Return the first non-empty workspace from ordered candidates.

    Adapters pass candidates from highest to lowest priority so each backend can
    keep its precedence rules while sharing the same normalization contract.
    """

    for candidate in candidates:
        if candidate is None:
            continue
        workspace = str(candidate).strip()
        if workspace:
            return workspace
    return default
