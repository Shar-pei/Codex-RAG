from __future__ import annotations

import json
import re
from typing import Optional, Type

from fastapi import HTTPException, Request
from pydantic import BaseModel

from lightrag.api.routers.ollama_models import SearchMode
from lightrag.utils import TiktokenTokenizer


async def parse_request_body(
    request: Request, model_class: Type[BaseModel]
) -> BaseModel:
    """
    Parse request body based on Content-Type header.
    Supports both application/json and application/octet-stream.

    Args:
        request: The FastAPI Request object
        model_class: The Pydantic model class to parse the request into

    Returns:
        An instance of the provided model_class
    """
    content_type = request.headers.get("content-type", "").lower()

    try:
        if content_type.startswith("application/json"):
            body = await request.json()
        elif content_type.startswith("application/octet-stream"):
            body_bytes = await request.body()
            body = json.loads(body_bytes.decode("utf-8"))
        else:
            body_bytes = await request.body()
            body = json.loads(body_bytes.decode("utf-8"))

        return model_class(**body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Error parsing request body: {str(exc)}"
        ) from exc


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in text using tiktoken."""
    tokens = TiktokenTokenizer().encode(text)
    return len(tokens)


def parse_query_mode(query: str) -> tuple[str, SearchMode, bool, Optional[str]]:
    """Parse query prefix to determine search mode.

    Returns tuple of (cleaned_query, search_mode, only_need_context, user_prompt).

    Examples:
    - "/local[use mermaid format for diagrams] query string" -> (cleaned_query, SearchMode.local, False, "use mermaid format for diagrams")
    - "/[use mermaid format for diagrams] query string" -> (cleaned_query, SearchMode.hybrid, False, "use mermaid format for diagrams")
    - "/local  query string" -> (cleaned_query, SearchMode.local, False, None)
    """
    user_prompt = None

    bracket_pattern = r"^/([a-z]*)\[(.*?)\](.*)"
    bracket_match = re.match(bracket_pattern, query)

    if bracket_match:
        mode_prefix = bracket_match.group(1)
        user_prompt = bracket_match.group(2)
        remaining_query = bracket_match.group(3).lstrip()
        query = f"/{mode_prefix} {remaining_query}".strip()

    mode_map = {
        "/local ": (SearchMode.local, False),
        "/global ": (SearchMode.global_, False),
        "/naive ": (SearchMode.naive, False),
        "/hybrid ": (SearchMode.hybrid, False),
        "/mix ": (SearchMode.mix, False),
        "/bypass ": (SearchMode.bypass, False),
        "/context": (SearchMode.mix, True),
        "/localcontext": (SearchMode.local, True),
        "/globalcontext": (SearchMode.global_, True),
        "/hybridcontext": (SearchMode.hybrid, True),
        "/naivecontext": (SearchMode.naive, True),
        "/mixcontext": (SearchMode.mix, True),
    }

    for prefix, (mode, only_need_context) in mode_map.items():
        if query.startswith(prefix):
            cleaned_query = query[len(prefix) :].lstrip()
            return cleaned_query, mode, only_need_context, user_prompt

    return query, SearchMode.mix, False, user_prompt
