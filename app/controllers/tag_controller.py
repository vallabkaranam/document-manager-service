from fastapi import HTTPException
from typing import List
from app.interfaces.tag_interface import TagInterface
from app.schemas.tag_schemas import Tag as Tag


class TagController:
    def __init__(self, tag_interface: TagInterface):
        self.tag_interface = tag_interface

    def get_all_tags(self) -> List[Tag]:
        try:
            return self.tag_interface.get_all_tags()
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting all tags: {str(e)}"
            )

    def create_tag(self, tag_text: str) -> Tag:
        try:
            return self.tag_interface.create_tag(tag_text)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating tag: {str(e)}"
            ) 