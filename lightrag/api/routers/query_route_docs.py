from __future__ import annotations


def _detail_response(error_description: str, detail_message: str) -> dict[int, dict]:
    return {
        400: {
            "description": "Bad Request - Invalid input parameters",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"detail": {"type": "string"}},
                    },
                    "example": {
                        "detail": "Query text must be at least 3 characters long"
                    },
                }
            },
        },
        500: {
            "description": error_description,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"detail": {"type": "string"}},
                    },
                    "example": {"detail": detail_message},
                }
            },
        },
    }


QUERY_ROUTE_RESPONSES = {
    200: {
        "description": "Successful RAG query response",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "The generated response from the RAG system",
                        },
                        "references": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "reference_id": {"type": "string"},
                                    "file_path": {"type": "string"},
                                    "content": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of chunk contents from this file (only included when include_chunk_content=True)",
                                    },
                                },
                            },
                            "description": "Reference list (only included when include_references=True)",
                        },
                    },
                    "required": ["response"],
                },
                "examples": {
                    "with_references": {
                        "summary": "Response with references",
                        "description": "Example response when include_references=True",
                        "value": {
                            "response": "Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines capable of performing tasks that typically require human intelligence, such as learning, reasoning, and problem-solving.",
                            "references": [
                                {
                                    "reference_id": "1",
                                    "file_path": "/documents/ai_overview.pdf",
                                },
                                {
                                    "reference_id": "2",
                                    "file_path": "/documents/machine_learning.txt",
                                },
                            ],
                        },
                    },
                    "with_chunk_content": {
                        "summary": "Response with chunk content",
                        "description": "Example response when include_references=True and include_chunk_content=True. Note: content is an array of chunks from the same file.",
                        "value": {
                            "response": "Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines capable of performing tasks that typically require human intelligence, such as learning, reasoning, and problem-solving.",
                            "references": [
                                {
                                    "reference_id": "1",
                                    "file_path": "/documents/ai_overview.pdf",
                                    "content": [
                                        "Artificial Intelligence (AI) represents a transformative field in computer science focused on creating systems that can perform tasks requiring human-like intelligence. These tasks include learning from experience, understanding natural language, recognizing patterns, and making decisions.",
                                        "AI systems can be categorized into narrow AI, which is designed for specific tasks, and general AI, which aims to match human cognitive abilities across a wide range of domains.",
                                    ],
                                },
                                {
                                    "reference_id": "2",
                                    "file_path": "/documents/machine_learning.txt",
                                    "content": [
                                        "Machine learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed. It focuses on the development of algorithms that can access data and use it to learn for themselves."
                                    ],
                                },
                            ],
                        },
                    },
                    "without_references": {
                        "summary": "Response without references",
                        "description": "Example response when include_references=False",
                        "value": {
                            "response": "Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines capable of performing tasks that typically require human intelligence, such as learning, reasoning, and problem-solving."
                        },
                    },
                    "different_modes": {
                        "summary": "Different query modes",
                        "description": "Examples of responses from different query modes",
                        "value": {
                            "local_mode": "Focuses on specific entities and their relationships",
                            "global_mode": "Provides broader context from relationship patterns",
                            "hybrid_mode": "Combines local and global approaches",
                            "naive_mode": "Simple vector similarity search",
                            "mix_mode": "Integrates knowledge graph and vector retrieval",
                        },
                    },
                },
            }
        },
    },
    **_detail_response(
        "Internal Server Error - Query processing failed",
        "Failed to process query: LLM service unavailable",
    ),
}


QUERY_STREAM_ROUTE_RESPONSES = {
    200: {
        "description": "Flexible RAG query response - format depends on stream parameter",
        "content": {
            "application/x-ndjson": {
                "schema": {
                    "type": "string",
                    "format": "ndjson",
                    "description": "Newline-delimited JSON (NDJSON) format used for both streaming and non-streaming responses. For streaming: multiple lines with separate JSON objects. For non-streaming: single line with complete JSON object.",
                    "example": '{"references": [{"reference_id": "1", "file_path": "/documents/ai.pdf"}]}\n{"response": "Artificial Intelligence is"}\n{"response": " a field of computer science"}\n{"response": " that focuses on creating intelligent machines."}',
                },
                "examples": {
                    "streaming_with_references": {
                        "summary": "Streaming mode with references (stream=true)",
                        "description": "Multiple NDJSON lines when stream=True and include_references=True. First line contains references, subsequent lines contain response chunks.",
                        "value": '{"references": [{"reference_id": "1", "file_path": "/documents/ai_overview.pdf"}, {"reference_id": "2", "file_path": "/documents/ml_basics.txt"}]}\n{"response": "Artificial Intelligence (AI) is a branch of computer science"}\n{"response": " that aims to create intelligent machines capable of performing"}\n{"response": " tasks that typically require human intelligence, such as learning,"}\n{"response": " reasoning, and problem-solving."}',
                    },
                    "streaming_with_chunk_content": {
                        "summary": "Streaming mode with chunk content (stream=true, include_chunk_content=true)",
                        "description": "Multiple NDJSON lines when stream=True, include_references=True, and include_chunk_content=True. First line contains references with content arrays (one file may have multiple chunks), subsequent lines contain response chunks.",
                        "value": '{"references": [{"reference_id": "1", "file_path": "/documents/ai_overview.pdf", "content": ["Artificial Intelligence (AI) represents a transformative field...", "AI systems can be categorized into narrow AI and general AI..."]}, {"reference_id": "2", "file_path": "/documents/ml_basics.txt", "content": ["Machine learning is a subset of AI that enables computers to learn..."]}]}\n{"response": "Artificial Intelligence (AI) is a branch of computer science"}\n{"response": " that aims to create intelligent machines capable of performing"}\n{"response": " tasks that typically require human intelligence."}',
                    },
                    "streaming_without_references": {
                        "summary": "Streaming mode without references (stream=true)",
                        "description": "Multiple NDJSON lines when stream=True and include_references=False. Only response chunks are sent.",
                        "value": '{"response": "Machine learning is a subset of artificial intelligence"}\n{"response": " that enables computers to learn and improve from experience"}\n{"response": " without being explicitly programmed for every task."}',
                    },
                    "non_streaming_with_references": {
                        "summary": "Non-streaming mode with references (stream=false)",
                        "description": "Single NDJSON line when stream=False and include_references=True. Complete response with references in one message.",
                        "value": '{"references": [{"reference_id": "1", "file_path": "/documents/neural_networks.pdf"}], "response": "Neural networks are computational models inspired by biological neural networks that consist of interconnected nodes (neurons) organized in layers. They are fundamental to deep learning and can learn complex patterns from data through training processes."}',
                    },
                    "non_streaming_without_references": {
                        "summary": "Non-streaming mode without references (stream=false)",
                        "description": "Single NDJSON line when stream=False and include_references=False. Complete response only.",
                        "value": '{"response": "Deep learning is a subset of machine learning that uses neural networks with multiple layers (hence deep) to model and understand complex patterns in data. It has revolutionized fields like computer vision, natural language processing, and speech recognition."}',
                    },
                    "error_response": {
                        "summary": "Error during streaming",
                        "description": "Error handling in NDJSON format when an error occurs during processing.",
                        "value": '{"references": [{"reference_id": "1", "file_path": "/documents/ai.pdf"}]}\n{"response": "Artificial Intelligence is"}\n{"error": "LLM service temporarily unavailable"}',
                    },
                },
            }
        },
    },
    **_detail_response(
        "Internal Server Error - Query processing failed",
        "Failed to process streaming query: Knowledge graph unavailable",
    ),
}


QUERY_DATA_ROUTE_RESPONSES = {
    200: {
        "description": "Successful data retrieval response with structured RAG data",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["success", "failure"],
                            "description": "Query execution status",
                        },
                        "message": {
                            "type": "string",
                            "description": "Status message describing the result",
                        },
                        "data": {
                            "type": "object",
                            "properties": {
                                "entities": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "entity_name": {"type": "string"},
                                            "entity_type": {"type": "string"},
                                            "description": {"type": "string"},
                                            "source_id": {"type": "string"},
                                            "file_path": {"type": "string"},
                                            "reference_id": {"type": "string"},
                                        },
                                    },
                                    "description": "Retrieved entities from knowledge graph",
                                },
                                "relationships": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "src_id": {"type": "string"},
                                            "tgt_id": {"type": "string"},
                                            "description": {"type": "string"},
                                            "keywords": {"type": "string"},
                                            "weight": {"type": "number"},
                                            "source_id": {"type": "string"},
                                            "file_path": {"type": "string"},
                                            "reference_id": {"type": "string"},
                                        },
                                    },
                                    "description": "Retrieved relationships from knowledge graph",
                                },
                                "chunks": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "content": {"type": "string"},
                                            "file_path": {"type": "string"},
                                            "chunk_id": {"type": "string"},
                                            "reference_id": {"type": "string"},
                                        },
                                    },
                                    "description": "Retrieved text chunks from vector database",
                                },
                                "references": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "reference_id": {"type": "string"},
                                            "file_path": {"type": "string"},
                                        },
                                    },
                                    "description": "Reference list for citation purposes",
                                },
                            },
                            "description": "Structured retrieval data containing entities, relationships, chunks, and references",
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "query_mode": {"type": "string"},
                                "keywords": {
                                    "type": "object",
                                    "properties": {
                                        "high_level": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "low_level": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                                "processing_info": {
                                    "type": "object",
                                    "properties": {
                                        "total_entities_found": {"type": "integer"},
                                        "total_relations_found": {"type": "integer"},
                                        "entities_after_truncation": {"type": "integer"},
                                        "relations_after_truncation": {"type": "integer"},
                                        "final_chunks_count": {"type": "integer"},
                                    },
                                },
                            },
                            "description": "Query metadata including mode, keywords, and processing information",
                        },
                    },
                    "required": ["status", "message", "data", "metadata"],
                },
                "examples": {
                    "successful_local_mode": {
                        "summary": "Local mode data retrieval",
                        "description": "Example of structured data from local mode query focusing on specific entities",
                        "value": {
                            "status": "success",
                            "message": "Query executed successfully",
                            "data": {
                                "entities": [
                                    {
                                        "entity_name": "Neural Networks",
                                        "entity_type": "CONCEPT",
                                        "description": "Computational models inspired by biological neural networks",
                                        "source_id": "chunk-123",
                                        "file_path": "/documents/ai_basics.pdf",
                                        "reference_id": "1",
                                    }
                                ],
                                "relationships": [
                                    {
                                        "src_id": "Neural Networks",
                                        "tgt_id": "Machine Learning",
                                        "description": "Neural networks are a subset of machine learning algorithms",
                                        "keywords": "subset, algorithm, learning",
                                        "weight": 0.85,
                                        "source_id": "chunk-123",
                                        "file_path": "/documents/ai_basics.pdf",
                                        "reference_id": "1",
                                    }
                                ],
                                "chunks": [
                                    {
                                        "content": "Neural networks are computational models that mimic the way biological neural networks work...",
                                        "file_path": "/documents/ai_basics.pdf",
                                        "chunk_id": "chunk-123",
                                        "reference_id": "1",
                                    }
                                ],
                                "references": [
                                    {
                                        "reference_id": "1",
                                        "file_path": "/documents/ai_basics.pdf",
                                    }
                                ],
                            },
                            "metadata": {
                                "query_mode": "local",
                                "keywords": {
                                    "high_level": ["neural", "networks"],
                                    "low_level": [
                                        "computation",
                                        "model",
                                        "algorithm",
                                    ],
                                },
                                "processing_info": {
                                    "total_entities_found": 5,
                                    "total_relations_found": 3,
                                    "entities_after_truncation": 1,
                                    "relations_after_truncation": 1,
                                    "final_chunks_count": 1,
                                },
                            },
                        },
                    },
                    "global_mode": {
                        "summary": "Global mode data retrieval",
                        "description": "Example of structured data from global mode query analyzing broader patterns",
                        "value": {
                            "status": "success",
                            "message": "Query executed successfully",
                            "data": {
                                "entities": [],
                                "relationships": [
                                    {
                                        "src_id": "Artificial Intelligence",
                                        "tgt_id": "Machine Learning",
                                        "description": "AI encompasses machine learning as a core component",
                                        "keywords": "encompasses, component, field",
                                        "weight": 0.92,
                                        "source_id": "chunk-456",
                                        "file_path": "/documents/ai_overview.pdf",
                                        "reference_id": "2",
                                    }
                                ],
                                "chunks": [],
                                "references": [
                                    {
                                        "reference_id": "2",
                                        "file_path": "/documents/ai_overview.pdf",
                                    }
                                ],
                            },
                            "metadata": {
                                "query_mode": "global",
                                "keywords": {
                                    "high_level": [
                                        "artificial",
                                        "intelligence",
                                        "overview",
                                    ],
                                    "low_level": [],
                                },
                            },
                        },
                    },
                    "naive_mode": {
                        "summary": "Naive mode data retrieval",
                        "description": "Example of structured data from naive mode using only vector search",
                        "value": {
                            "status": "success",
                            "message": "Query executed successfully",
                            "data": {
                                "entities": [],
                                "relationships": [],
                                "chunks": [
                                    {
                                        "content": "Deep learning is a subset of machine learning that uses neural networks with multiple layers...",
                                        "file_path": "/documents/deep_learning.pdf",
                                        "chunk_id": "chunk-789",
                                        "reference_id": "3",
                                    }
                                ],
                                "references": [
                                    {
                                        "reference_id": "3",
                                        "file_path": "/documents/deep_learning.pdf",
                                    }
                                ],
                            },
                            "metadata": {
                                "query_mode": "naive",
                                "keywords": {"high_level": [], "low_level": []},
                            },
                        },
                    },
                },
            }
        },
    },
    **_detail_response(
        "Internal Server Error - Data retrieval failed",
        "Failed to retrieve data: Knowledge graph unavailable",
    ),
}
