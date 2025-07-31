"""
RAG Routes Module

This module defines the HTTP API routes for querying documents using
Retrieval-Augmented Generation (RAG) pipelines.

These routes are designed for dual consumption:
1. By human developers and frontend consumers
2. By machine reasoning agents and LLM-based tools via an MCP (Model-Context-Protocol) server

All endpoints are documented with descriptive docstrings and designed to support introspectable,
semantically clear interactions for tools and agents.

Assumptions:
- Retrieval uses pgvector for semantic search across chunk embeddings
- Thematic tags may be incorporated for improved retrieval context
- User authentication is currently not enforced (e.g., hardcoded user_id=1)
- Prompt construction and generation are handled by the controller using an OpenAI-compatible LLM
"""

from fastapi import APIRouter, Depends, HTTPException
from app.controllers.rag_controller import RAGController
from app.interfaces.document_embedding_interface import DocumentEmbeddingInterface
from app.interfaces.openai_interface import OpenAIInterface
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.interfaces.tag_interface import TagInterface
from app.schemas.rag_schemas import RAGQueryRequest, RAGQueryResponse

router = APIRouter()

# --------------------------
# Dependency Injection Setup
# --------------------------

def get_document_embedding_interface(db: Session = Depends(get_db)) -> DocumentEmbeddingInterface:
    """Injects the document embedding DB interface."""
    return DocumentEmbeddingInterface(db)

def get_tag_interface(db: Session = Depends(get_db)) -> TagInterface:
    """Injects the tag DB interface."""
    return TagInterface(db)

def get_openai_interface() -> OpenAIInterface:
    """Injects the OpenAI API interface for summarization."""
    return OpenAIInterface()

def get_rag_controller(
    document_embedding_interface: DocumentEmbeddingInterface = Depends(get_document_embedding_interface),
    tag_interface: TagInterface = Depends(get_tag_interface),
    openai_interface: OpenAIInterface = Depends(get_openai_interface)
) -> RAGController:
    """Constructs the RAGController with necessary interfaces."""
    return RAGController(document_embedding_interface, tag_interface, openai_interface)

# --------------------------
# Route Definitions
# --------------------------

@router.post("/query", response_model=RAGQueryResponse)
async def handle_query(
    request: RAGQueryRequest,
    rag_controller: RAGController = Depends(get_rag_controller)
) -> RAGQueryResponse:
    """
    Query documents using Retrieval-Augmented Generation (RAG).

    Args:
        request (RAGQueryRequest): User query payload, including the question and optional context.

    Returns:
        RAGQueryResponse: LLM-generated response grounded in relevant documents.

    Notes:
        - Performs semantic search to find relevant documents.
        - Extracts context from those documents.
        - Constructs a prompt and invokes the LLM to generate a grounded response.
    """
    try:
        response = await rag_controller.handle_query(request)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")