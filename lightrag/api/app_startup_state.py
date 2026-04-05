from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from lightrag.api.frontend_build_checker import check_frontend_build


_FRONTEND_OUTDATED_SUFFIX = "\u26A0\uFE0F"


@dataclass
class AppStartupState:
    webui_assets_exist: bool
    api_version_display: str
    api_key: str | None
    doc_manager: Any
    webui_title: str | None
    webui_description: str | None


def build_app_startup_state(
    args, api_version: str, document_manager_factory=None
) -> AppStartupState:
    """Derive startup-only app state before route registration."""
    webui_assets_exist, is_frontend_outdated = check_frontend_build()
    api_version_display = (
        f"{api_version}{_FRONTEND_OUTDATED_SUFFIX}"
        if is_frontend_outdated
        else api_version
    )

    if document_manager_factory is None:
        from lightrag.api.routers.document_routes import DocumentManager

        document_manager_factory = DocumentManager

    return AppStartupState(
        webui_assets_exist=webui_assets_exist,
        api_version_display=api_version_display,
        api_key=os.getenv("LIGHTRAG_API_KEY") or args.key,
        doc_manager=document_manager_factory(args.input_dir, workspace=args.workspace),
        webui_title=os.getenv("WEBUI_TITLE"),
        webui_description=os.getenv("WEBUI_DESCRIPTION"),
    )
