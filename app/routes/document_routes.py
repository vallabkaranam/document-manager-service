"""
Document Routes Module

This module defines the HTTP API routes for document-related operations in the system,
including upload, retrieval, updating, deletion, tag associations, search, and summarization.

These routes are designed for dual consumption:
1. By human developers and frontend consumers
2. By machine reasoning agents and LLM-based tools via an MCP (Model-Context-Protocol) server

All endpoints are documented with descriptive docstrings and designed to support introspectable,
semantically clear interactions for tools and agents.

Assumptions:
- User authentication is currently not enforced (e.g., hardcoded user_id=1)
- Tagging relies on a background async worker and event-driven processing via EventBridge
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

# Caching and DB session management
from app.cache.cache import Cache
from app.cache.redis import redis_client 
from app.db.session import get_db

# Core business logic controllers and interfaces
from app.controllers.document_controller import DocumentController
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.document_tag_interface import DocumentTagInterface
from app.interfaces.openai_interface import OpenAIInterface
from app.interfaces.eventbridge_interface import EventBridgeInterface
from app.interfaces.s3_interface import S3Interface
from app.interfaces.summary_interface import SummaryInterface
from app.interfaces.tag_interface import TagInterface

# Pydantic schemas for request and response validation
from app.schemas.document_schemas import (
    Document,
    DocumentsResponse,
    DocumentsSearchRequest,
    DocumentsSearchResponse,
    UploadDocumentRequest,
    DocumentUpdate
)
from app.schemas.document_tag_schemas import DocumentTag
from app.schemas.summary_schemas import Summary

router = APIRouter()


# --------------------------
# Dependency Injection Setup
# --------------------------

def get_s3_interface() -> S3Interface:
    """Injects the S3 interface with bucket name from env."""
    return S3Interface(os.getenv("S3_BUCKET_NAME"))

def get_eventbridge_interface() -> EventBridgeInterface:
    """Injects the EventBridge interface for emitting document processing events."""
    return EventBridgeInterface()

def get_document_interface(db: Session = Depends(get_db)) -> DocumentInterface:
    """Injects the document DB interface."""
    return DocumentInterface(db)

def get_document_tag_interface(db: Session = Depends(get_db)) -> DocumentTagInterface:
    """Injects the document-tag relational interface."""
    return DocumentTagInterface(db)

def get_openai_interface() -> OpenAIInterface:
    """Injects the OpenAI API interface for summarization."""
    return OpenAIInterface()

def get_summary_interface(db: Session = Depends(get_db)) -> SummaryInterface:
    """Injects the summary DB interface."""
    return SummaryInterface(db)

def get_tag_interface(db: Session = Depends(get_db)) -> TagInterface:
    """Injects the tag DB interface."""
    return TagInterface(db)

def get_cache() -> Cache:
    """Injects the Redis cache layer."""
    return Cache(redis_client)

def get_document_controller(
    s3_interface: S3Interface = Depends(get_s3_interface),
    eventbridge_interface: EventBridgeInterface = Depends(get_eventbridge_interface),
    document_interface: DocumentInterface = Depends(get_document_interface),
    document_tag_interface: DocumentTagInterface = Depends(get_document_tag_interface),
    openai_interface: OpenAIInterface = Depends(get_openai_interface),
    summary_interface: SummaryInterface = Depends(get_summary_interface),
    tag_interface: TagInterface = Depends(get_tag_interface),
    cache: Cache = Depends(get_cache)
) -> DocumentController:
    """
    Constructs the core DocumentController by injecting all dependencies.
    
    This controller encapsulates all business logic related to documents,
    including creation, association, search, and summarization.
    """
    return DocumentController(
        s3_interface,
        eventbridge_interface,
        document_interface,
        document_tag_interface,
        openai_interface,
        summary_interface,
        tag_interface,
        cache
    )


# --------------------------
# Route Definitions
# --------------------------

@router.get("/documents", response_model=DocumentsResponse, operation_id="get_documents_by_user", summary="Get all documents by user ID")
async def get_documents_by_user_id(user_id: int, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentsResponse:
    """
    Retrieve all documents uploaded by a specific user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        DocumentsResponse: A list of documents owned by the user.
    
    Notes:
        Currently assumes user_id is passed explicitly. Will need auth middleware later.
    """
    try:
        documents = document_controller.get_documents_by_user_id(user_id)
        return DocumentsResponse(documents=documents)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to get documents by user id: {str(e)}")


@router.get("/tags/{tag_id}/documents", response_model=DocumentsResponse, operation_id="get_documents_by_tag", summary="Get all documents by tag ID")
async def get_documents_by_tag_id(tag_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentsResponse:
    """
    Retrieve all documents associated with a given tag ID.

    Args:
        tag_id (str): UUID of the tag.

    Returns:
        DocumentsResponse: A list of documents tagged with the specified tag.
    """
    try:
        documents = document_controller.get_documents_by_tag_id(tag_id)
        return DocumentsResponse(documents=documents)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to get documents for tag with id {tag_id}: {str(e)}")


@router.get("/documents/{document_id}", response_model=Document, operation_id="get_document_by_id", summary="Get document metadata by ID")
async def get_document_by_id(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> Document:
    """
    Retrieve metadata for a specific document by ID.

    Args:
        document_id (str): UUID of the document.

    Returns:
        Document: Metadata for the requested document.
    """
    try:
        document = document_controller.get_document_by_document_id(document_id)
        return document
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to get document by id: {str(e)}")


@router.get("/documents/{document_id}/view", operation_id="get_document_presigned_url", summary="Get presigned URL for viewing a document")
async def view_document_by_id(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> str:
    """
    Generate and return a presigned URL for viewing the document.

    Args:
        document_id (str): UUID of the document.

    Returns:
        str: A time-limited S3 URL to access the document.
    """
    try:
        return document_controller.view_document_by_id(document_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to get presigned url for document: {str(e)}")


@router.post("/documents", response_model=Document, operation_id="upload_document", summary="Upload a new document")
async def upload_document(
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_controller: DocumentController = Depends(get_document_controller)
) -> Document:
    """
    Uploads a new document and stores metadata in the database.

    Args:
        file (UploadFile): The file to upload.
        filename (Optional[str]): Optional filename override.
        description (Optional[str]): Optional document description.

    Returns:
        Document: Metadata of the uploaded document.
    
    Behavior:
        - Uploads to S3
        - Stores metadata in DB
        - Emits DocumentReady event for tagging
    """
    request = UploadDocumentRequest(filename=filename, description=description)
    try:
        document = document_controller.upload_document(file, request)
        return document
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while uploading document: {str(e)}")


@router.patch("/documents/{document_id}", response_model=Document, operation_id="update_document", summary="Update document metadata")
async def update_document(document_id: str, update_data: DocumentUpdate, document_controller: DocumentController = Depends(get_document_controller)) -> Document:
    """
    Partially update document metadata.

    Args:
        document_id (str): UUID of the document.
        update_data (DocumentUpdate): Fields to update.

    Returns:
        Document: The updated document metadata.
    """
    try:
        document = document_controller.partial_update_document(document_id, update_data)
        return document
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


@router.delete("/documents/{document_id}", response_model=Document, operation_id="delete_document", summary="Delete a document")
async def delete_document(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> Document:
    """
    Delete a document and return its metadata.

    Args:
        document_id (str): UUID of the document.

    Returns:
        Document: Metadata of the deleted document.
    
    Notes:
        Also deletes all associated summaries, tag relationships, and metadata.
        Underlying S3 object is not deleted though.
    """
    try:
        document = document_controller.delete_document(document_id)
        return document 
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post("/documents/{document_id}/tags/{tag_id}", response_model=DocumentTag, operation_id="associate_document_tag", summary="Associate a document with a tag")
async def associate_document_and_tag(document_id: str, tag_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentTag:
    """
    Associate a document with a tag.

    Args:
        document_id (str): UUID of the document.
        tag_id (str): UUID of the tag.

    Returns:
        DocumentTag: The association object created.
    """
    try:
        link = document_controller.associate_tag_and_document(document_id, tag_id)
        return link
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to associate document {document_id} with tag {tag_id}: {str(e)}")


@router.delete("/documents/{document_id}/tags/{tag_id}", response_model=DocumentTag, operation_id="unassociate_document_tag", summary="Remove association between document and tag")
async def unassociate_document_and_tag(document_id: str, tag_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentTag:
    """
    Remove the association between a document and a tag.

    Args:
        document_id (str): UUID of the document.
        tag_id (str): UUID of the tag.

    Returns:
        DocumentTag: The association object removed.

    Notes:
        Only deletes the link between the document and tag.
        The tag and document remain intact unless independently deleted.
    """
    try:
        link = document_controller.unassociate_document_and_tag(document_id, tag_id)
        return link
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unassociate document {document_id} with tag {tag_id}: {str(e)}")


@router.get("/documents/{document_id}/summarize", response_model=Summary, operation_id="summarize_document", summary="Generate a summary for the document")
async def summarize_document_by_document_id(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> Summary:
    """
    Generate a natural language summary for a document.

    Args:
        document_id (str): UUID of the document.

    Returns:
        Summary: Summary object containing the generated summary.

    Notes:
        If a summary exists, it returns the cached version.
        Otherwise, downloads file, extracts text, sends to OpenAI, stores result.
    """
    try:
        summary = await document_controller.summarize_document_by_document_id(document_id)
        return summary
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize document {document_id}: {str(e)}")


@router.post("/documents/search", response_model=DocumentsSearchResponse, operation_id="search_documents", summary="Search documents by semantic similarity")
def search_for_documents(body: DocumentsSearchRequest, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentsSearchResponse:
    """
    Semantic search across documents using tags and embeddings.

    Args:
        body (DocumentsSearchRequest): Search query payload.

    Returns:
        DocumentsSearchResponse: Matching documents and relevant tags.

    Behavior:
        - Embeds the query
        - Finds semantically similar tags
        - Returns associated documents
    """
    try:
        similar_documents_and_tags = document_controller.search_for_documents(body)
        return similar_documents_and_tags
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find similar documents based on the query: {body.query}")