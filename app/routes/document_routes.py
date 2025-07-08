import os
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.controllers.document_controller import DocumentController
from app.db.session import get_db
from app.interfaces.queue_interface import QueueInterface
from app.interfaces.s3_interface import S3Interface
from app.interfaces.document_interface import DocumentInterface
from app.schemas.document_schemas import Document, DocumentsResponse, UploadDocumentRequest, UploadDocumentResponse, DocumentUpdate

router = APIRouter()

def get_s3_interface() -> S3Interface:
    return S3Interface(os.getenv("S3_BUCKET_NAME"))

def get_queue_interface() -> QueueInterface:
    return QueueInterface(os.getenv("SQS_QUEUE_URL"))

def get_document_interface(db: Session = Depends(get_db)) -> DocumentInterface:
    return DocumentInterface(db)

def get_document_controller(
    s3_interface: S3Interface = Depends(get_s3_interface),
    queue_interface: QueueInterface = Depends(get_queue_interface),
    document_interface: DocumentInterface = Depends(get_document_interface)
) -> DocumentController:
    return DocumentController(s3_interface, queue_interface, document_interface)

@router.get("/documents")
async def get_documents_by_user_id(user_id: int, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentsResponse:
    try:
        documents = document_controller.get_documents_by_user_id(user_id)
        return DocumentsResponse(documents=documents)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get documents by user id: {str(e)}"
        )
    
@router.get("/documents/{document_id}", response_model=Document)
async def get_document_by_id(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> Document:
    try:
        document = document_controller.get_document_by_document_id(document_id)
        return document
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get document by id: {str(e)}"
        )

@router.get("/documents/{document_id}/view")
async def view_document_by_id(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> str:
    try:
        return document_controller.view_document_by_id(document_id)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get document by id: {str(e)}"
        )

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_controller: DocumentController = Depends(get_document_controller)
) -> UploadDocumentResponse:
    request = UploadDocumentRequest(filename=filename, description=description)
    
    try:
        document, tags = document_controller.upload_document(file, request)
        return UploadDocumentResponse(
            document=document,
            tags=tags
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )
    
@router.patch("/documents/{document_id}", response_model=Document)
async def update_document(document_id: str, update_data: DocumentUpdate, document_controller: DocumentController = Depends(get_document_controller)) -> Document:
    try:
        return document_controller.partial_update_document(document_id, update_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update document: {str(e)}"
        )
    
    

