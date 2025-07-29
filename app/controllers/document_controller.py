"""
Document Controller Module

This module encapsulates the core business logic for document-related operations,
including upload, deletion, metadata management, tag associations, OpenAI summarization,
semantic search, and S3 access. It acts as an intermediary between FastAPI routes
and database/storage/external service layers.

The controller is designed to be stateless and testable, with all external dependencies
injected at initialization.

Key Capabilities:
- Upload documents to S3 and create DB entries
- Trigger ML-based auto-tagging via EventBridge events
- Retrieve documents by user, tag, or ID
- Generate secure presigned URLs
- Manage document-tag relationships
- Generate summaries using OpenAI, with Redis caching
- Perform semantic search using vector embeddings

Assumptions:
- Uploads are PDF-compatible (text extracted via `PyPDF2`)
- Only the latest summary per document is returned
- Document metadata and S3 paths are stored centrally
- Caching uses a time-to-live of 10 minutes
"""

from typing import List
from urllib.parse import urlparse
from fastapi import HTTPException, UploadFile
from app.cache.cache import Cache
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.document_tag_interface import DocumentTagInterface
from app.interfaces.openai_interface import OpenAIInterface
from app.interfaces.eventbridge_interface import EventBridgeInterface
from app.interfaces.s3_interface import S3Interface
from app.interfaces.summary_interface import SummaryInterface
from app.interfaces.tag_interface import TagInterface
from app.schemas.document_tag_schemas import DocumentTag
from app.schemas.errors import (
    DocumentCreationError, DocumentDeletionError, DocumentNotFoundError, DocumentTagLinkError, DocumentTagNotFoundError, DocumentUpdateError, SimilarTagSearchError, TagNotFoundError,
    OpenAIServiceError, EventBridgeEmitError, S3PresignedUrlError, S3UploadError, SummaryCreationError
)
from app.ml_models.embedding_models import shared_sentence_model
import httpx

from app.schemas.document_schemas import Document, DocumentUpdate, DocumentsSearchRequest, DocumentsSearchResponse, UploadDocumentRequest
from app.schemas.summary_schemas import Summary
from app.utils.document_utils import embed_text, extract_text_from_pdf, generate_unique_filename


class DocumentController:
    """
    Controller for managing all document-related business logic.

    Args:
        s3_interface (S3Interface): Handles storage and retrieval of document files.
        eventbridge_interface (EventBridgeInterface): Emits events for document processing.
        document_interface (DocumentInterface): Database CRUD for documents.
        document_tag_interface (DocumentTagInterface): Manages document-tag associations.
        openai_interface (OpenAIInterface): Summarizes text using GPT models.
        summary_interface (SummaryInterface): Stores and retrieves document summaries.
        tag_interface (TagInterface): Retrieves tags, including similarity-based.
        cache (Cache): Redis-backed cache layer.
    """
    
    def __init__(self, 
                 s3_interface: S3Interface, 
                 eventbridge_interface: EventBridgeInterface, 
                 document_interface: DocumentInterface, 
                 document_tag_interface: DocumentTagInterface, 
                 openai_interface: OpenAIInterface, 
                 summary_interface: SummaryInterface, 
                 tag_interface: TagInterface, 
                 cache: Cache
                 ) -> None:
        self.s3_interface = s3_interface
        self.eventbridge_interface = eventbridge_interface
        self.document_interface = document_interface
        self.document_tag_interface = document_tag_interface
        self.openai_interface = openai_interface
        self.summary_interface = summary_interface
        self.tag_interface = tag_interface
        self.cache = cache
        self.model = shared_sentence_model


    def upload_document(self, file: UploadFile, document_input: UploadDocumentRequest) -> Document:
        """
        Uploads a document to S3, stores metadata in DB, and emits event for auto-tagging.

        Args:
            file (UploadFile): The uploaded file object (PDF, image, etc.).
            document_input (UploadDocumentRequest): Optional metadata.

        Returns:
            Document: Metadata of the created document.

        Raises:
            HTTPException: If any step fails (S3, DB, EventBridge).

        Behavior:
            - Stores file in S3
            - Creates document entry in DB
            - Emits DocumentReady event for background processing
        """
        try:
            file_content = file.file.read()
            file.file.seek(0)  # reset pointer to beginning for any downstream reads

            # Choose filename: use custom filename if provided, otherwise use original filename
            chosen_filename = document_input.filename or file.filename
            # Generate unique filename before uploading
            unique_filename = generate_unique_filename(chosen_filename)
            
            # Pass the file content to upload_file
            s3_url = self.s3_interface.upload_file(file_content, unique_filename)

            # Create a document record in the database
            document = self.document_interface.create_document(
                s3_url=s3_url,
                filename=chosen_filename,
                content_type=file.content_type,
                size=file.size,
                description=document_input.description
            )
            
            # Emit event for async document processing
            self.eventbridge_interface.emit_document_ready_event(
                document_id=str(document.id),
                s3_url=document.storage_path,
                content_type=document.content_type
            )

            # Instead of waiting for tagging, return early        
            return document
        
        except (S3UploadError, EventBridgeEmitError, DocumentCreationError) as e:
            raise HTTPException(status_code=500, detail=str(e))

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"S3 upload error: {str(e)}")


    def get_documents_by_user_id(self, user_id: int) -> List[Document]:
        """
        Fetch all documents belonging to a specific user.

        Args:
            user_id (int): The user's ID.

        Returns:
            List[Document]: All documents for the user.
        """
        try:
            return self.document_interface.get_documents_by_user_id(user_id)
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting document by user id: {str(e)}")


    def get_document_by_document_id(self, document_id: str) -> Document:
        """
        Fetch a single document by its UUID.

        Args:
            document_id (str): UUID of the document.

        Returns:
            Document: Document metadata.
        """
        try:
            return self.document_interface.get_document_by_id(document_id)
        
        except DocumentNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"Error getting document by id: {str(e)}"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting document by document id: {str(e)}")


    def get_documents_by_tag_id(self, tag_id: str) -> List[Document]:
        """
        Fetch all documents that are associated with a specific tag.

        Args:
            tag_id (str): UUID of the tag.

        Returns:
            List[Document]: Documents linked to the tag.
        """
        try:
            return self.document_interface.get_documents_by_tag_id(tag_id)
        
        except TagNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to find tag: {str(e)}"
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting documents by tag id: {str(e)}")


    def view_document_by_id(self, document_id: str) -> str:
        """
        Generate a presigned S3 URL to view the document file.

        Args:
            document_id (str): UUID of the document.

        Returns:
            str: A time-limited URL for downloading/viewing.

        Notes:
            Used by frontend to securely access raw file content.
        """
        try:
            # take doc id and get document
            document = self.document_interface.get_document_by_id(document_id)

            # get storage path from doc object
            storage_path = document.storage_path
            # parse
            parsed = urlparse(storage_path)
            key = parsed.path.lstrip("/") 

            # pass that key into generate_presigned_url
            return self.s3_interface.generate_presigned_url(key)
        
        except DocumentNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except S3PresignedUrlError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )

        except HTTPException as e:
            raise e

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error in view_document_by_id: {str(e)}"
            )
        
    def partial_update_document(self, document_id: str, update_data: DocumentUpdate) -> Document:
        """
        Update document metadata (e.g., filename, description) partially.

        Args:
            document_id (str): UUID of the document.
            update_data (DocumentUpdate): Fields to update.

        Returns:
            Document: Updated document object.
        """
        try:
            return self.document_interface.update_document(document_id, update_data)
        
        except DocumentNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DocumentUpdateError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error updating document: {str(e)}"
            )
        
        except HTTPException as e:
            raise e
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")
        
    def delete_document(self, document_id: str) -> Document:
        """
        Delete a document and cascade-delete related metadata.

        Args:
            document_id (str): UUID of the document.

        Returns:
            Document: Deleted document metadata.

        Notes:
            - Cascades through document_tag and summary tables.
            - S3 deletion may occur in future enhancement.
        """
        try:
            return self.document_interface.delete_document(document_id)
        
        except DocumentNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DocumentDeletionError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document: {str(e)}"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
        
    def associate_tag_and_document(self, document_id: str, tag_id: str) -> DocumentTag:
        """
        Link a document to a tag.

        Args:
            document_id (str): UUID of the document.
            tag_id (str): UUID of the tag.

        Returns:
            DocumentTag: Link object between document and tag.
        """
        try:
            return self.document_tag_interface.link_document_tag(document_id, tag_id)
        
        except (DocumentNotFoundError, TagNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DocumentTagLinkError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Association failed: {str(e)}"
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error associating document and tag: {str(e)}")

    def unassociate_document_and_tag(self, document_id: str, tag_id: str) -> DocumentTag:
        """
        Unlink a tag from a document.

        Args:
            document_id (str): UUID of the document.
            tag_id (str): UUID of the tag.

        Returns:
            DocumentTag: Removed association object.
        """
        try:
            return self.document_tag_interface.unlink_document_tag(document_id, tag_id)
        
        except (DocumentNotFoundError, TagNotFoundError, DocumentTagNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DocumentTagLinkError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unassociation failed: {str(e)}"
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error unassociating document and tag: {str(e)}")


    async def summarize_document_by_document_id(self, document_id: str) -> Summary:
        """
        Generate or retrieve a summary for a document using OpenAI.

        Args:
            document_id (str): UUID of the document.

        Returns:
            Summary: Latest summary object.

        Behavior:
            - Checks cache (and thereby db) for existing summary
            - Otherwise, downloads file from S3
            - Extracts text (PDFs only for now)
            - Summarizes using OpenAI
            - Caches the result for 10 mins
        """
        try:
            async def summarize_document():
                summaries = self.summary_interface.get_summaries_by_document_id(document_id)

                if summaries:
                    # return the latest summary
                    return summaries[0]
                
                # If no summaries available for document:

                # Step 1: Get presigned URL from storage path
                presigned_url = self.view_document_by_id(document_id)

                # Step 2: Download file from S3 using async HTTP client
                async with httpx.AsyncClient() as client:
                    response = await client.get(presigned_url)
                    response.raise_for_status()

                # Step 3: Extract bytes and text
                file_bytes = await response.aread()
                text = extract_text_from_pdf(file_bytes)

                # Step 4: Pass to GPT for summarization
                response = await self.openai_interface.summarize_text(text)

                # Create summary db object
                created_summary = self.summary_interface.create_summary_by_document_id(document_id, response.summary)
                return created_summary
            
            return await self.cache.get_or_set(f"document_summary:{document_id}", summarize_document, ttl=600)
        
        except (SummaryCreationError, OpenAIServiceError) as e:
            raise HTTPException(status_code=500, detail=str(e))

        except HTTPException as e:
            raise e
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error summarizing document: {str(e)}")
        
    def search_for_documents(self, request: DocumentsSearchRequest) -> DocumentsSearchResponse:
        """
        Perform semantic search over documents using tag embeddings.

        Args:
            request (DocumentsSearchRequest): Natural language query.

        Returns:
            DocumentsSearchResponse: Matching documents and relevant tags.

        Behavior:
            - Embeds the query
            - Finds similar tags
            - Aggregates unique documents tagged accordingly
        """
        try:
            query_embedding = embed_text(request.query)
            tags = self.tag_interface.get_similar_tags(query_embedding)

            doc_dict = {}
            for tag in tags:
                try:
                    for doc in self.get_documents_by_tag_id(str(tag.id)):
                        doc_dict[doc.id] = doc
                except TagNotFoundError:
                    print(f"tag {str(tag.id)} not found")
                    continue

            documents = list(doc_dict.values())

            return DocumentsSearchResponse(
                documents=documents,
                tags=tags
            )
        
        except SimilarTagSearchError as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        
        except HTTPException as e:
            raise e
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error searching for similar documents: {str(e)}")