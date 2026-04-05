from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from lightrag.base import QueryParam


class QueryRequest(BaseModel):
    query: str = Field(
        min_length=3,
        description="The query text",
    )

    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = Field(
        default="mix",
        description="Query mode",
    )

    only_need_context: Optional[bool] = Field(
        default=None,
        description="If True, only returns the retrieved context without generating a response.",
    )

    only_need_prompt: Optional[bool] = Field(
        default=None,
        description="If True, only returns the generated prompt without producing a response.",
    )

    response_type: Optional[str] = Field(
        min_length=1,
        default=None,
        description="Defines the response format. Examples: 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points'.",
    )

    top_k: Optional[int] = Field(
        ge=1,
        default=None,
        description="Number of top items to retrieve. Represents entities in 'local' mode and relationships in 'global' mode.",
    )

    chunk_top_k: Optional[int] = Field(
        ge=1,
        default=None,
        description="Number of text chunks to retrieve initially from vector search and keep after reranking.",
    )

    max_entity_tokens: Optional[int] = Field(
        default=None,
        description="Maximum number of tokens allocated for entity context in unified token control system.",
        ge=1,
    )

    max_relation_tokens: Optional[int] = Field(
        default=None,
        description="Maximum number of tokens allocated for relationship context in unified token control system.",
        ge=1,
    )

    max_total_tokens: Optional[int] = Field(
        default=None,
        description="Maximum total tokens budget for the entire query context (entities + relations + chunks + system prompt).",
        ge=1,
    )

    hl_keywords: list[str] = Field(
        default_factory=list,
        description="List of high-level keywords to prioritize in retrieval. Leave empty to use the LLM to generate the keywords.",
    )

    ll_keywords: list[str] = Field(
        default_factory=list,
        description="List of low-level keywords to refine retrieval focus. Leave empty to use the LLM to generate the keywords.",
    )

    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Stores past conversation history to maintain context. Format: [{'role': 'user/assistant', 'content': 'message'}].",
    )

    user_prompt: Optional[str] = Field(
        default=None,
        description="User-provided prompt for the query. If provided, this will be used instead of the default value from prompt template.",
    )

    enable_rerank: Optional[bool] = Field(
        default=None,
        description="Enable reranking for retrieved text chunks. If True but no rerank model is configured, a warning will be issued. Default is True.",
    )

    include_references: Optional[bool] = Field(
        default=True,
        description="If True, includes reference list in responses. Affects /query and /query/stream endpoints. /query/data always includes references.",
    )

    include_chunk_content: Optional[bool] = Field(
        default=False,
        description="If True, includes actual chunk text content in references. Only applies when include_references=True. Useful for evaluation and debugging.",
    )

    stream: Optional[bool] = Field(
        default=True,
        description="If True, enables streaming output for real-time responses. Only affects /query/stream endpoint.",
    )

    @field_validator("query", mode="after")
    @classmethod
    def query_strip_after(cls, query: str) -> str:
        return query.strip()

    @field_validator("conversation_history", mode="after")
    @classmethod
    def conversation_history_role_check(
        cls, conversation_history: List[Dict[str, Any]] | None
    ) -> List[Dict[str, Any]] | None:
        if conversation_history is None:
            return None
        for msg in conversation_history:
            if "role" not in msg:
                raise ValueError("Each message must have a 'role' key.")
            if not isinstance(msg["role"], str) or not msg["role"].strip():
                raise ValueError("Each message 'role' must be a non-empty string.")
        return conversation_history

    def to_query_params(self, is_stream: bool) -> QueryParam:
        """Converts a QueryRequest instance into a QueryParam instance."""
        request_data = self.model_dump(
            exclude_none=True, exclude={"query", "include_chunk_content"}
        )
        param = QueryParam(**request_data)
        param.stream = is_stream
        return param


class ReferenceItem(BaseModel):
    """A single reference item in query responses."""

    reference_id: str = Field(description="Unique reference identifier")
    file_path: str = Field(description="Path to the source file")
    content: Optional[List[str]] = Field(
        default=None,
        description="List of chunk contents from this file (only present when include_chunk_content=True)",
    )


class QueryResponse(BaseModel):
    response: str = Field(
        description="The generated response",
    )
    references: Optional[List[ReferenceItem]] = Field(
        default=None,
        description="Reference list (Disabled when include_references=False, /query/data always includes references.)",
    )


class QueryDataResponse(BaseModel):
    status: str = Field(description="Query execution status")
    message: str = Field(description="Status message")
    data: Dict[str, Any] = Field(
        description="Query result data containing entities, relationships, chunks, and references"
    )
    metadata: Dict[str, Any] = Field(
        description="Query metadata including mode, keywords, and processing information"
    )


class StreamChunkResponse(BaseModel):
    """Response model for streaming chunks in NDJSON format"""

    references: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Reference list (only in first chunk when include_references=True)",
    )
    response: Optional[str] = Field(
        default=None, description="Response content chunk or complete response"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if processing fails"
    )
