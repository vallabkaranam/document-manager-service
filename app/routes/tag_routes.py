from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.controllers.tag_controller import TagController
from app.db.session import get_db
from app.interfaces.tag_interface import TagInterface
from app.schemas.tag_schemas import Tag, CreateTagRequest, TagsResponse

router = APIRouter()

def get_tag_interface(db: Session = Depends(get_db)) -> TagInterface:
    return TagInterface(db)

def get_tag_controller(
    tag_interface: TagInterface = Depends(get_tag_interface)
) -> TagController:
    return TagController(tag_interface)

@router.get("/tags", response_model=TagsResponse)
async def get_all_tags(tag_controller: TagController = Depends(get_tag_controller)) -> TagsResponse:
    try:
        tags = tag_controller.get_all_tags()
        return TagsResponse(tags=tags)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get all tags: {str(e)}"
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