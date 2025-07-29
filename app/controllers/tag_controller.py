"""
Tag Controller Module

This module encapsulates the business logic for tag-related operations, acting as a bridge
between FastAPI routes, database interfaces, and caching layers. It ensures that tags
can be created, fetched, updated, and deleted with consistent error handling, cache management,
and separation of concerns.

The controller is designed to be stateless and testable, with dependencies such as database
interfaces and cache injected at initialization.

Key Capabilities:
- Retrieve all tags with Redis caching
- Create new tags and invalidate cache
- Delete existing tags and invalidate cache
- Update tag content partially
- Fetch individual tags by ID
- Retrieve all tags linked to a document ID

Assumptions:
- All tag operations are lightweight and synchronous except for cache-based retrieval
- Tag uniqueness or validation is handled at the DB interface layer
- Redis cache TTL is set to 10 minutes for `get_all_tags`
"""

from fastapi import HTTPException
from typing import List
from app.cache.cache import Cache
from app.interfaces.tag_interface import TagInterface
from app.schemas.errors import (
    DocumentNotFoundError,
    TagCreationError,
    TagDeletionError,
    TagNotFoundError,
    TagUpdateError
)
from app.schemas.tag_schemas import Tag as Tag, TagUpdate
from app.utils.document_utils import embed_text


class TagController:
    def __init__(self, tag_interface: TagInterface, cache: Cache) -> None:
        """
        Controller class responsible for tag-related business logic.

        Args:
            tag_interface (TagInterface): Interface for interacting with tag data.
            cache (Cache): Caching layer to optimize repeated tag fetches.
        """
        self.tag_interface = tag_interface
        self.cache = cache
        self._tag_cache_key = "tags:all"  # Global cache key for all tags

    async def get_all_tags(self) -> List[Tag]:
        """
        Retrieve all tags in the system, using cache to reduce DB load.

        Returns:
            List[Tag]: A list of all tag objects.
        """
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
        """
        Create a new tag with the given text and invalidate the cache.

        Args:
            tag_text (str): Text content of the new tag.

        Returns:
            Tag: The newly created tag object.
        """
        try:
            self.cache.delete(self._tag_cache_key)
            embedding_vector = embed_text(tag_text)
            return self.tag_interface.create_tag(tag_text, embedding_vector)
        
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
        """
        Delete the tag with the given ID and invalidate the cache.

        Args:
            tag_id (str): The UUID of the tag to delete.

        Returns:
            Tag: The deleted tag object.
        """
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
        """
        Retrieve a single tag by its ID.

        Args:
            tag_id (str): The UUID of the tag to fetch.

        Returns:
            Tag: The tag object corresponding to the given ID.
        """
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
        """
        Partially update the tag with the given ID and invalidate the cache.

        Args:
            tag_id (str): The UUID of the tag to update.
            update_data (TagUpdate): Fields to update.

        Returns:
            Tag: The updated tag object.
        """
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
        
    def get_tags_by_document_id(self, document_id: str) -> List[Tag]:
        """
        Retrieve all tags associated with a given document.

        Args:
            document_id (str): The UUID of the document.

        Returns:
            List[Tag]: A list of tags linked to the document.
        """
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
        
