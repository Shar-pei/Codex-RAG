from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm


def create_auth_router(auth_handler: Any, version_payload: dict[str, Any]) -> APIRouter:
    router = APIRouter()

    @router.get("/auth-status")
    async def get_auth_status():
        if not auth_handler.accounts:
            return {
                "auth_configured": False,
                **_build_guest_access_payload(auth_handler, version_payload),
            }

        return {
            "auth_configured": True,
            "auth_mode": "enabled",
            **version_payload,
        }

    @router.post("/login")
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        if not auth_handler.accounts:
            return _build_guest_access_payload(auth_handler, version_payload)

        username = form_data.username
        if auth_handler.accounts.get(username) != form_data.password:
            raise HTTPException(status_code=401, detail="Incorrect credentials")

        user_token = auth_handler.create_token(
            username=username,
            role="user",
            metadata={"auth_mode": "enabled"},
        )
        return {
            "access_token": user_token,
            "token_type": "bearer",
            "auth_mode": "enabled",
            **version_payload,
        }

    return router


def _build_guest_access_payload(
    auth_handler: Any, version_payload: dict[str, Any]
) -> dict[str, Any]:
    guest_token = auth_handler.create_token(
        username="guest",
        role="guest",
        metadata={"auth_mode": "disabled"},
    )
    return {
        "access_token": guest_token,
        "token_type": "bearer",
        "auth_mode": "disabled",
        "message": "Authentication is disabled. Using guest access.",
        **version_payload,
    }
