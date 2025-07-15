from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.cache.cache import Cache
from app.cache.redis import redis_client 
from app.controllers.tag_controller import TagController
from app.db.session import get_db
from app.interfaces.tag_interface import TagInterface
from app.schemas.tag_schemas import Tag, CreateTagRequest, TagUpdate, TagsResponse

router = APIRouter()

def get_tag_interface(db: Session = Depends(get_db)) -> TagInterface:
    return TagInterface(db)

def get_cache() -> Cache:
    return Cache(redis_client)

def get_tag_controller(
    tag_interface: TagInterface = Depends(get_tag_interface),
    cache: Cache = Depends(get_cache)
) -> TagController:
    return TagController(tag_interface, cache)

@router.get("/tags", response_model=TagsResponse)
async def get_all_tags(tag_controller: TagController = Depends(get_tag_controller)) -> TagsResponse:
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

@router.get("/tags/{document_id}", response_model=TagsResponse)
async def get_tags_by_document_id(document_id: str, tag_controller: TagController = Depends(get_tag_controller)) -> TagsResponse:
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

@router.post("/tags", response_model=Tag)
async def create_tag(
    tag_request: CreateTagRequest,
    tag_controller: TagController = Depends(get_tag_controller)
) -> Tag:
    try:
        return tag_controller.create_tag(tag_request.text)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create tag: {str(e)}"
        ) 

@router.delete("/tags/{tag_id}", response_model=Tag)
async def delete_tag(
    tag_id: str,
    tag_controller: TagController = Depends(get_tag_controller)    
) -> Tag:
    try:
        return tag_controller.delete_tag(tag_id)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete tag: {str(e)}"
        )

@router.get("/tags/{tag_id}", response_model=Tag)
async def get_tag_by_id(
    tag_id: str,
    tag_controller: TagController = Depends(get_tag_controller)
) -> Tag:
    try:
        return tag_controller.get_tag_by_id(tag_id)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to get tag by id: {str(e)}'
        )

@router.patch("/tags/{tag_id}", response_model=Tag)
async def update_tag(tag_id: str, update_data: TagUpdate, tag_controller: TagController = Depends(get_tag_controller)) -> Tag:
    try:
        return tag_controller.partial_update_tag(tag_id, update_data)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update tag: {str(e)}"
        )