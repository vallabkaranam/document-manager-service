import os
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.controllers.document_controller import DocumentController
from app.db.session import get_db
from app.interfaces.document_tag_interface import DocumentTagInterface
from app.interfaces.openai_interface import OpenAIInterface
from app.interfaces.queue_interface import QueueInterface
from app.interfaces.s3_interface import S3Interface
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.summary_interface import SummaryInterface
from app.schemas.document_schemas import Document, DocumentsResponse, UploadDocumentRequest, DocumentUpdate
from app.schemas.document_tag_schemas import DocumentTag
from app.schemas.openai_schemas import OpenAISummaryResponse
from app.schemas.summary_schemas import Summary

router = APIRouter()

def get_s3_interface() -> S3Interface:
    return S3Interface(os.getenv("S3_BUCKET_NAME"))

def get_queue_interface() -> QueueInterface:
    return QueueInterface(os.getenv("SQS_QUEUE_URL"))

def get_document_interface(db: Session = Depends(get_db)) -> DocumentInterface:
    return DocumentInterface(db)

def get_document_tag_interface(db: Session = Depends(get_db)) -> DocumentTagInterface:
    return DocumentTagInterface(db)

def get_openai_interface() -> OpenAIInterface:
    return OpenAIInterface()

def get_summary_interface(db: Session = Depends(get_db)) -> SummaryInterface:
    return SummaryInterface(db)


def get_document_controller(
    s3_interface: S3Interface = Depends(get_s3_interface),
    queue_interface: QueueInterface = Depends(get_queue_interface),
    document_interface: DocumentInterface = Depends(get_document_interface),
    document_tag_interface: DocumentTagInterface = Depends(get_document_tag_interface),
    openai_interface: OpenAIInterface = Depends(get_openai_interface),
    summary_interface: SummaryInterface = Depends(get_summary_interface)
) -> DocumentController:
    return DocumentController(s3_interface, queue_interface, document_interface, document_tag_interface, openai_interface, summary_interface)

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
    
@router.get("/documents/{tag_id}")
async def get_documents_by_tag_id(tag_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> DocumentsResponse:
    try:
        documents = document_controller.get_documents_by_tag_id(tag_id)
        return DocumentsResponse(documents=documents)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to get documents for tag with id {tag_id}: {str(e)}"
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

@router.post("/upload-document", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_controller: DocumentController = Depends(get_document_controller)
) -> Document:
    request = UploadDocumentRequest(filename=filename, description=description)
    
    try:
        document = document_controller.upload_document(file, request)
        return document
    
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
    
@router.delete("/documents/{document_id}", response_model=Document)
async def delete_document(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> Document:
    try:
        return document_controller.delete_document(document_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
    
@router.post("/documents/{document_id}/tags/{tag_id}", response_model=DocumentTag)
async def associate_document_and_tag(document_id: str, tag_id: str, document_controller: DocumentController = Depends(get_document_controller)):
    try:
        return document_controller.associate_tag_and_document(document_id, tag_id)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to associate document {document_id} with tag {tag_id}: {str(e)}"
        )

@router.delete("/documents/{document_id}/tags/{tag_id}", response_model=DocumentTag)
async def unassociate_document_and_tag(document_id: str, tag_id: str, document_controller: DocumentController = Depends(get_document_controller)):
    try:
        return document_controller.unassociate_document_and_tag(document_id, tag_id)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unassociate document {document_id} with tag {tag_id}: {str(e)}"
        )

@router.get("/documents/{document_id}/summarize", response_model=Summary)
async def summarize_document_by_document_id(document_id: str, document_controller: DocumentController = Depends(get_document_controller)) -> Summary:
    try:
        return await document_controller.summarize_document_by_document_id(document_id)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to summarize document {document_id}: {str(e)}"
        )

