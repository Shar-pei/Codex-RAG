"""
This module contains all query-related routes for the LightRAG API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.utils import logger
from lightrag.api.routers.query_models import (
    QueryDataResponse,
    QueryRequest,
    QueryResponse,
    ReferenceItem as _ReferenceItem,
    StreamChunkResponse as _StreamChunkResponse,
)
from lightrag.api.routers.query_execution import (
    build_query_data_param as _build_query_data_param,
    build_query_text_param as _build_query_text_param,
    execute_query_data_request as _execute_query_data_request,
    execute_query_text_request as _execute_query_text_request,
    normalize_query_data_response as _normalize_query_data_response,
)
from lightrag.api.routers.query_route_docs import (
    QUERY_DATA_ROUTE_RESPONSES as _QUERY_DATA_ROUTE_RESPONSES,
    QUERY_ROUTE_RESPONSES as _QUERY_ROUTE_RESPONSES,
    QUERY_STREAM_ROUTE_RESPONSES as _QUERY_STREAM_ROUTE_RESPONSES,
)
from lightrag.api.routers.query_response_helpers import (
    build_query_response_model as _build_query_response_model,
    build_stream_complete_payload as _build_stream_complete_payload,
    get_query_response_content as _get_query_response_content,
    prepare_query_references as _prepare_query_references,
)
from lightrag.api.routers.query_streaming import (
    build_query_streaming_response as _build_query_streaming_response,
    iter_query_stream_payloads as _iter_query_stream_payloads,
)

router = APIRouter(tags=["query"])

ReferenceItem = _ReferenceItem
StreamChunkResponse = _StreamChunkResponse
QUERY_ROUTE_RESPONSES = _QUERY_ROUTE_RESPONSES
QUERY_STREAM_ROUTE_RESPONSES = _QUERY_STREAM_ROUTE_RESPONSES
QUERY_DATA_ROUTE_RESPONSES = _QUERY_DATA_ROUTE_RESPONSES
build_query_text_param = _build_query_text_param
build_query_data_param = _build_query_data_param
execute_query_text_request = _execute_query_text_request
normalize_query_data_response = _normalize_query_data_response
execute_query_data_request = _execute_query_data_request
prepare_query_references = _prepare_query_references
get_query_response_content = _get_query_response_content
build_query_response_model = _build_query_response_model
build_stream_complete_payload = _build_stream_complete_payload
iter_query_stream_payloads = _iter_query_stream_payloads
build_query_streaming_response = _build_query_streaming_response


def create_query_routes(rag, api_key: Optional[str] = None, top_k: int = 60):
    combined_auth = get_combined_auth_dependency(api_key)

    @router.post(
        "/query",
        response_model=QueryResponse,
        dependencies=[Depends(combined_auth)],
        responses=QUERY_ROUTE_RESPONSES,
    )
    async def query_text(request: QueryRequest):
        """
        Comprehensive RAG query endpoint with non-streaming response. Parameter "stream" is ignored.

        This endpoint performs Retrieval-Augmented Generation (RAG) queries using various modes
        to provide intelligent responses based on your knowledge base.

        **Query Modes:**
        - **local**: Focuses on specific entities and their direct relationships
        - **global**: Analyzes broader patterns and relationships across the knowledge graph
        - **hybrid**: Combines local and global approaches for comprehensive results
        - **naive**: Simple vector similarity search without knowledge graph
        - **mix**: Integrates knowledge graph retrieval with vector search (recommended)
        - **bypass**: Direct LLM query without knowledge retrieval

        conversation_history parameteris sent to LLM only, does not affect retrieval results.

        **Usage Examples:**

        Basic query:
        ```json
        {
            "query": "What is machine learning?",
            "mode": "mix"
        }
        ```

        Bypass initial LLM call by providing high-level and low-level keywords:
        ```json
        {
            "query": "What is Retrieval-Augmented-Generation?",
            "hl_keywords": ["machine learning", "information retrieval", "natural language processing"],
            "ll_keywords": ["retrieval augmented generation", "RAG", "knowledge base"],
            "mode": "mix"
        }
        ```

        Advanced query with references:
        ```json
        {
            "query": "Explain neural networks",
            "mode": "hybrid",
            "include_references": true,
            "response_type": "Multiple Paragraphs",
            "top_k": 10
        }
        ```

        Conversation with history:
        ```json
        {
            "query": "Can you give me more details?",
            "conversation_history": [
                {"role": "user", "content": "What is AI?"},
                {"role": "assistant", "content": "AI is artificial intelligence..."}
            ]
        }
        ```

        Args:
            request (QueryRequest): The request object containing query parameters:
                - **query**: The question or prompt to process (min 3 characters)
                - **mode**: Query strategy - "mix" recommended for best results
                - **include_references**: Whether to include source citations
                - **response_type**: Format preference (e.g., "Multiple Paragraphs")
                - **top_k**: Number of top entities/relations to retrieve
                - **conversation_history**: Previous dialogue context
                - **max_total_tokens**: Token budget for the entire response

        Returns:
            QueryResponse: JSON response containing:
                - **response**: The generated answer to your query
                - **references**: Source citations (if include_references=True)

        Raises:
            HTTPException:
                - 400: Invalid input parameters (e.g., query too short)
                - 500: Internal processing error (e.g., LLM service unavailable)
        """
        try:
            return await execute_query_text_request(rag, request)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/query/stream",
        dependencies=[Depends(combined_auth)],
        responses=QUERY_STREAM_ROUTE_RESPONSES,
    )
    async def query_text_stream(request: QueryRequest):
        """
        Advanced RAG query endpoint with flexible streaming response.

        This endpoint provides the most flexible querying experience, supporting both real-time streaming
        and complete response delivery based on your integration needs.

        **Response Modes:**
        - Real-time response delivery as content is generated
        - NDJSON format: each line is a separate JSON object
        - First line: `{"references": [...]}` (if include_references=True)
        - Subsequent lines: `{"response": "content chunk"}`
        - Error handling: `{"error": "error message"}`

        > If stream parameter is False, or the query hit LLM cache, complete response delivered in a single streaming message.

        **Response Format Details**
        - **Content-Type**: `application/x-ndjson` (Newline-Delimited JSON)
        - **Structure**: Each line is an independent, valid JSON object
        - **Parsing**: Process line-by-line, each line is self-contained
        - **Headers**: Includes cache control and connection management

        **Query Modes (same as /query endpoint)**
        - **local**: Entity-focused retrieval with direct relationships
        - **global**: Pattern analysis across the knowledge graph
        - **hybrid**: Combined local and global strategies
        - **naive**: Vector similarity search only
        - **mix**: Integrated knowledge graph + vector retrieval (recommended)
        - **bypass**: Direct LLM query without knowledge retrieval

        conversation_history parameteris sent to LLM only, does not affect retrieval results.

        **Usage Examples**

        Real-time streaming query:
        ```json
        {
            "query": "Explain machine learning algorithms",
            "mode": "mix",
            "stream": true,
            "include_references": true
        }
        ```

        Bypass initial LLM call by providing high-level and low-level keywords:
        ```json
        {
            "query": "What is Retrieval-Augmented-Generation?",
            "hl_keywords": ["machine learning", "information retrieval", "natural language processing"],
            "ll_keywords": ["retrieval augmented generation", "RAG", "knowledge base"],
            "mode": "mix"
        }
        ```

        Complete response query:
        ```json
        {
            "query": "What is deep learning?",
            "mode": "hybrid",
            "stream": false,
            "response_type": "Multiple Paragraphs"
        }
        ```

        Conversation with context:
        ```json
        {
            "query": "Can you elaborate on that?",
            "stream": true,
            "conversation_history": [
                {"role": "user", "content": "What is neural network?"},
                {"role": "assistant", "content": "A neural network is..."}
            ]
        }
        ```

        **Response Processing:**

        ```python
        async for line in response.iter_lines():
            data = json.loads(line)
            if "references" in data:
                # Handle references (first message)
                references = data["references"]
            if "response" in data:
                # Handle content chunk
                content_chunk = data["response"]
            if "error" in data:
                # Handle error
                error_message = data["error"]
        ```

        **Error Handling:**
        - Streaming errors are delivered as `{"error": "message"}` lines
        - Non-streaming errors raise HTTP exceptions
        - Partial responses may be delivered before errors in streaming mode
        - Always check for error objects when processing streaming responses

        Args:
            request (QueryRequest): The request object containing query parameters:
                - **query**: The question or prompt to process (min 3 characters)
                - **mode**: Query strategy - "mix" recommended for best results
                - **stream**: Enable streaming (True) or complete response (False)
                - **include_references**: Whether to include source citations
                - **response_type**: Format preference (e.g., "Multiple Paragraphs")
                - **top_k**: Number of top entities/relations to retrieve
                - **conversation_history**: Previous dialogue context for multi-turn conversations
                - **max_total_tokens**: Token budget for the entire response

        Returns:
            StreamingResponse: NDJSON streaming response containing:
                - **Streaming mode**: Multiple JSON objects, one per line
                  - References object (if requested): `{"references": [...]}`
                  - Content chunks: `{"response": "chunk content"}`
                  - Error objects: `{"error": "error message"}`
                - **Non-streaming mode**: Single JSON object
                  - Complete response: `{"references": [...], "response": "complete content"}`

        Raises:
            HTTPException:
                - 400: Invalid input parameters (e.g., query too short, invalid mode)
                - 500: Internal processing error (e.g., LLM service unavailable)

        Note:
            This endpoint is ideal for applications requiring flexible response delivery.
            Use streaming mode for real-time interfaces and non-streaming for batch processing.
        """
        try:
            # Use the stream parameter from the request, defaulting to True if not specified
            stream_mode = request.stream if request.stream is not None else True
            param = request.to_query_params(stream_mode)

            # Unified approach: always use aquery_llm for all cases
            result = await rag.aquery_llm(request.query, param=param)
            return build_query_streaming_response(
                result,
                include_references=request.include_references,
                include_chunk_content=request.include_chunk_content,
            )
        except Exception as e:
            logger.error(f"Error processing streaming query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/query/data",
        response_model=QueryDataResponse,
        dependencies=[Depends(combined_auth)],
        responses=QUERY_DATA_ROUTE_RESPONSES,
    )
    async def query_data(request: QueryRequest):
        """
        Advanced data retrieval endpoint for structured RAG analysis.

        This endpoint provides raw retrieval results without LLM generation, perfect for:
        - **Data Analysis**: Examine what information would be used for RAG
        - **System Integration**: Get structured data for custom processing
        - **Debugging**: Understand retrieval behavior and quality
        - **Research**: Analyze knowledge graph structure and relationships

        **Key Features:**
        - No LLM generation - pure data retrieval
        - Complete structured output with entities, relationships, and chunks
        - Always includes references for citation
        - Detailed metadata about processing and keywords
        - Compatible with all query modes and parameters

        **Query Mode Behaviors:**
        - **local**: Returns entities and their direct relationships + related chunks
        - **global**: Returns relationship patterns across the knowledge graph
        - **hybrid**: Combines local and global retrieval strategies
        - **naive**: Returns only vector-retrieved text chunks (no knowledge graph)
        - **mix**: Integrates knowledge graph data with vector-retrieved chunks
        - **bypass**: Returns empty data arrays (used for direct LLM queries)

        **Data Structure:**
        - **entities**: Knowledge graph entities with descriptions and metadata
        - **relationships**: Connections between entities with weights and descriptions
        - **chunks**: Text segments from documents with source information
        - **references**: Citation information mapping reference IDs to file paths
        - **metadata**: Processing information, keywords, and query statistics

        **Usage Examples:**

        Analyze entity relationships:
        ```json
        {
            "query": "machine learning algorithms",
            "mode": "local",
            "top_k": 10
        }
        ```

        Explore global patterns:
        ```json
        {
            "query": "artificial intelligence trends",
            "mode": "global",
            "max_relation_tokens": 2000
        }
        ```

        Vector similarity search:
        ```json
        {
            "query": "neural network architectures",
            "mode": "naive",
            "chunk_top_k": 5
        }
        ```

        Bypass initial LLM call by providing high-level and low-level keywords:
        ```json
        {
            "query": "What is Retrieval-Augmented-Generation?",
            "hl_keywords": ["machine learning", "information retrieval", "natural language processing"],
            "ll_keywords": ["retrieval augmented generation", "RAG", "knowledge base"],
            "mode": "mix"
        }
        ```

        **Response Analysis:**
        - **Empty arrays**: Normal for certain modes (e.g., naive mode has no entities/relationships)
        - **Processing info**: Shows retrieval statistics and token usage
        - **Keywords**: High-level and low-level keywords extracted from query
        - **Reference mapping**: Links all data back to source documents

        Args:
            request (QueryRequest): The request object containing query parameters:
                - **query**: The search query to analyze (min 3 characters)
                - **mode**: Retrieval strategy affecting data types returned
                - **top_k**: Number of top entities/relationships to retrieve
                - **chunk_top_k**: Number of text chunks to retrieve
                - **max_entity_tokens**: Token limit for entity context
                - **max_relation_tokens**: Token limit for relationship context
                - **max_total_tokens**: Overall token budget for retrieval

        Returns:
            QueryDataResponse: Structured JSON response containing:
                - **status**: "success" or "failure"
                - **message**: Human-readable status description
                - **data**: Complete retrieval results with entities, relationships, chunks, references
                - **metadata**: Query processing information and statistics

        Raises:
            HTTPException:
                - 400: Invalid input parameters (e.g., query too short, invalid mode)
                - 500: Internal processing error (e.g., knowledge graph unavailable)

        Note:
            This endpoint always includes references regardless of the include_references parameter,
            as structured data analysis typically requires source attribution.
        """
        try:
            return await execute_query_data_request(rag, request)
        except Exception as e:
            logger.error(f"Error processing data query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    return router
