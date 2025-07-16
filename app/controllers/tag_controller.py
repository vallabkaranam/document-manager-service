from fastapi import HTTPException
from typing import List
from app.cache.cache import Cache
from app.interfaces.tag_interface import TagInterface
from app.schemas.errors import DocumentNotFoundError, TagCreationError, TagDeletionError, TagNotFoundError, TagUpdateError
from app.schemas.tag_schemas import Tag as Tag, TagUpdate, TagsResponse


class TagController:
    def __init__(self, tag_interface: TagInterface, cache: Cache) -> None:
        self.tag_interface = tag_interface
        self.cache = cache
        self._tag_cache_key = "tags:all"

    async def get_all_tags(self) -> List[Tag]:
        try:
            def fetch_tags_from_db():
                return self.tag_interface.get_all_tags()
            
            return await self.cache.get_or_set(self._tag_cache_key, fetch_tags_from_db, ttl=600)

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting all tags: {str(e)}"
            )

    def create_tag(self, tag_text: str) -> Tag:
        try:
            self.cache.delete(self._tag_cache_key)
            return self.tag_interface.create_tag(tag_text)
        
        except TagCreationError as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating tag: {str(e)}"
            ) 
    
    def delete_tag(self, tag_id: str) -> Tag:
        try:
            self.cache.delete(self._tag_cache_key)
            return self.tag_interface.delete_tag(tag_id)
        
        except TagNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        
        except TagDeletionError as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting tag: {str(e)}"
            )
    
    def get_tag_by_id(self, tag_id: str) -> Tag:
        try:
            return self.tag_interface.get_tag_by_id(tag_id)
        
        except TagNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting tag by id: {str(e)}"
            )
    
    def partial_update_tag(self, tag_id: str, update_data: TagUpdate) -> Tag:
        try:
            self.cache.delete(self._tag_cache_key)
            return self.tag_interface.update_tag(tag_id, update_data)
        
        except TagNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        
        except TagUpdateError as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error updating tag: {str(e)}"
            )
        
    def get_tags_by_document_id(self, document_id: str) -> TagsResponse:
        try:
            return self.tag_interface.get_tags_by_document_id(document_id)
        
        except DocumentNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting tags by document id: {str(e)}"
            )
        
