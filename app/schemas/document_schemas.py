from typing import Optional
from pydantic import BaseModel, Field


class UploadDocumentRequest(BaseModel):
    filename: Optional[str] = Field(
                          default=None,
                          description="The name of the file",
                          example="filename.pdf")
    description: Optional[str] = Field(
                             default=None,
                             description="The description of the file",
                             example="Description of the filename")