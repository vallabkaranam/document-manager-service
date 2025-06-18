import os
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.controllers.document_controller import DocumentController
from app.db.session import get_db
from app.interfaces.s3_interface import S3Interface
from app.schemas.document_schemas import UploadDocumentRequest

router = APIRouter()

def get_s3_interface() -> S3Interface:
    return S3Interface(os.getenv("S3_BUCKET_NAME"))

def get_document_controller(s3_interface: S3Interface = Depends(get_s3_interface)) -> DocumentController:
    return DocumentController(s3_interface)

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_controller: DocumentController = Depends(get_document_controller)):

    request = UploadDocumentRequest(filename=filename, description=description)
    try: 
        return document_controller.upload_document(file, request)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Faild to upload document: {str(e)}"
        )
    
    

