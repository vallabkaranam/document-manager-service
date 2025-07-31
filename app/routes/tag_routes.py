"""
Tag Routes Module

This module defines the HTTP API routes for managing tags in the system,
including creation, retrieval, updating, deletion, and tag-document associations.

These routes are designed for dual consumption:
1. By human developers and frontend consumers
2. By machine reasoning agents and LLM-based tools via an MCP (Model-Context-Protocol) server

All endpoints are documented with descriptive docstrings and designed to support introspectable,
semantically clear interactions for tools and agents.

Assumptions:
- User authentication is currently not enforced (e.g., tags are not scoped per-user)
- Tag creation is idempotent only if de-duped at the DB layer
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Caching and DB session management
from app.cache.cache import Cache
from app.cache.redis import redis_client 
from app.controllers.tag_controller import TagController
from app.db.session import get_db

# Core DB interface and data schemas
from app.interfaces.tag_interface import TagInterface
from app.schemas.tag_schemas import Tag, CreateTagRequest, TagUpdate, TagsResponse

router = APIRouter()


# --------------------------
# Dependency Injection Setup
# --------------------------

def get_tag_interface(db: Session = Depends(get_db)) -> TagInterface:
    """Injects the tag DB interface."""
    return TagInterface(db)

def get_cache() -> Cache:
    """Injects the Redis cache layer."""
    return Cache(redis_client)

def get_tag_controller(
    tag_interface: TagInterface = Depends(get_tag_interface),
    cache: Cache = Depends(get_cache)
) -> TagController:
    """
    Constructs the TagController by injecting DB and cache dependencies.

    This controller encapsulates all business logic related to tag management.
    """
    return TagController(tag_interface, cache)


# --------------------------
# Route Definitions
# --------------------------

@router.get(
    "/tags",
    response_model=TagsResponse,
    operation_id="get_all_tags",
    summary="Retrieve all tags"
)
async def get_all_tags(tag_controller: TagController = Depends(get_tag_controller)) -> TagsResponse:
    """
    Retrieve all tags in the system.

    Returns:
        TagsResponse: A list of all tags.

    Notes:
        Not currently filtered by user or permissions.
        Cached for performance.
    """
    try:
        tags = await tag_controller.get_all_tags()
        return TagsResponse(tags=tags)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get all tags: {str(e)}"
        )


@router.get(
    "/documents/{document_id}/tags",
    response_model=TagsResponse,
    operation_id="get_tags_by_document",
    summary="Retrieve tags for a document"
)
async def get_tags_by_document_id(document_id: str, tag_controller: TagController = Depends(get_tag_controller)) -> TagsResponse:
    """
    Retrieve all tags associated with a given document.

    Args:
        document_id (str): UUID of the document.

    Returns:
        TagsResponse: A list of tags linked to the specified document.

    Notes:
        Assumes that document-tag relationships are many-to-many.
    """
    try:
        tags = tag_controller.get_tags_by_document_id(document_id)
        return TagsResponse(tags=tags)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get tags for document with id {document_id}: {str(e)}"
        )


@router.post(
    "/tags",
    response_model=Tag,
    operation_id="create_tag",
    summary="Create a new tag"
)
async def create_tag(
    tag_request: CreateTagRequest,
    tag_controller: TagController = Depends(get_tag_controller)
) -> Tag:
    """
    Create a new tag with the given text.

    Args:
        tag_request (CreateTagRequest): Payload containing tag text.

    Returns:
        Tag: The created tag metadata.

    Behavior:
        Adds new tag to DB if not existing
        May be enhanced in the future with per-user scoping

    Assumptions:
        No deduplication is enforced in this layer.
    """
    try:
        tag = tag_controller.create_tag(tag_request.text)
        return tag
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create tag: {str(e)}"
        )


@router.delete(
    "/tags/{tag_id}",
    response_model=Tag,
    operation_id="delete_tag",
    summary="Delete a tag by ID"
)
async def delete_tag(
    tag_id: str,
    tag_controller: TagController = Depends(get_tag_controller)    
) -> Tag:
    """
    Delete a tag by its UUID.

    Args:
        tag_id (str): UUID of the tag to delete.

    Returns:
        Tag: Metadata of the deleted tag.

    Notes:
        Also deletes all associated document-tag relationships
        Documents and their summaries remain unaffected
    """
    try:
        tag = tag_controller.delete_tag(tag_id)
        return tag
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete tag: {str(e)}"
        )


@router.get(
    "/tags/{tag_id}",
    response_model=Tag,
    operation_id="get_tag_by_id",
    summary="Get tag metadata by ID"
)
async def get_tag_by_id(
    tag_id: str,
    tag_controller: TagController = Depends(get_tag_controller)
) -> Tag:
    """
    Retrieve metadata for a specific tag by ID.

    Args:
        tag_id (str): UUID of the tag.

    Returns:
        Tag: Metadata for the requested tag.
    """
    try:
        tag = tag_controller.get_tag_by_id(tag_id)
        return tag
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to get tag by id: {str(e)}'
        )


@router.patch(
    "/tags/{tag_id}",
    response_model=Tag,
    operation_id="update_tag",
    summary="Update tag metadata"
)
async def update_tag(tag_id: str, update_data: TagUpdate, tag_controller: TagController = Depends(get_tag_controller)) -> Tag:
    """
    Partially update tag metadata (e.g., text).

    Args:
        tag_id (str): UUID of the tag.
        update_data (TagUpdate): Fields to update.

    Returns:
        Tag: The updated tag metadata.
    """
    try:
        tag = tag_controller.partial_update_tag(tag_id, update_data)
        return tag
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update tag: {str(e)}"
        )