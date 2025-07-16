from urllib.parse import urlparse
from fastapi import HTTPException
from app.schemas.errors import (
    DocumentNotFoundError, DocumentTagLinkError, DocumentTagNotFoundError, SimilarTagSearchError, TagNotFoundError,
    OpenAIServiceError, SQSMessageSendError, S3PresignedUrlError, S3UploadError, SummaryCreationError
)
from app.ml_models.embedding_models import shared_sentence_model
import httpx

from app.schemas.document_schemas import DocumentsSearchResponse
from app.schemas.summary_schemas import Summary
from app.utils.document_utils import embed_text, extract_text_from_pdf, generate_unique_filename


class DocumentController:
    def __init__(self, s3_interface, queue_interface, document_interface, document_tag_interface, openai_interface, summary_interface, tag_interface, cache):
        self.s3_interface = s3_interface
        self.queue_interface = queue_interface
        self.document_interface = document_interface
        self.document_tag_interface = document_tag_interface
        self.openai_interface = openai_interface
        self.summary_interface = summary_interface
        self.tag_interface = tag_interface
        self.cache = cache
        self.model = shared_sentence_model

    # ✅ 2. Document Upload API
    # Endpoint: POST /documents/
    # Accepts: file upload (PDF, image, etc.), optional description
    # Stores file in S3 or local /uploads/ directory
    # Returns: metadata (filename, size, upload time, storage path)

    # ✅ 3. Auto-Tagging with ML Model
    # On upload, run an ML model (e.g., image classifier or keyword extractor)
    # Automatically attach a list of relevant tags to the document
    # Store tags in a normalized table
    def upload_document(self, file, document_input):
        # Accepts: file upload (PDF, image, etc.), optional description

        # Stores file in S3
        try:
            # Read the file content from the UploadFile object
            file_content = file.file.read()
            # Reset the file pointer to the beginning
            file.file.seek(0)

            # Choose filename: use custom filename if provided, otherwise use original filename
            chosen_filename = document_input.filename or file.filename
            # Generate unique filename before uploading
            unique_filename = generate_unique_filename(chosen_filename)
            
            # Pass the file content to upload_file
            s3_url = self.s3_interface.upload_file(file_content, unique_filename)

            # Create a document record in the database
            document = self.document_interface.create_document(
                s3_url=s3_url,
                filename=document_input.filename or file.filename,
                content_type=file.content_type,
                size=file.size,
                description=document_input.description
            )
            
            # Send message to queue for async processing
            self.queue_interface.send_document_tagging_message(
                document_id=document.id,
                s3_url=document.storage_path,
                content_type=document.content_type
            )

            # Instead of waiting for tagging, return early        
            return document
        
        except S3UploadError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to storage: {str(e)}"
            )

        except SQSMessageSendError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue document for tagging: {str(e)}"
            )

        except HTTPException as e:
            raise e
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"S3 upload error: {str(e)}"
            )
    
    def get_documents_by_user_id(self, user_id):
        try:
            return self.document_interface.get_documents_by_user_id(user_id)
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting document by user id: {str(e)}"
            )
    
    def get_document_by_document_id(self, document_id):
        try:
            return self.document_interface.get_document_by_id(document_id)

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting document by document id: {str(e)}"
            ) 
    
    def get_documents_by_tag_id(self, tag_id):
        try:
            return self.document_interface.get_documents_by_tag_id(tag_id)
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting documents by tag id: {str(e)}"
            ) 
    
    def view_document_by_id(self, document_id):
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
        
    def partial_update_document(self, document_id, update_data):
        try:
            return self.document_interface.update_document(document_id, update_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")
        
    def delete_document(self, document_id):
        try:
            return self.document_interface.delete_document(document_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
        
    def associate_tag_and_document(self, document_id, tag_id):
        try:
            return self.document_tag_interface.link_document_tag(document_id, tag_id)
        
        except (DocumentNotFoundError, TagNotFoundError) as e:
            raise HTTPException(
                status_code=404,
                detail=f"Association failed: {str(e)}"
                )
        
        except DocumentTagLinkError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Association failed: {str(e)}"
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error associating document and tag: {str(e)}"
            ) 
    
    def unassociate_document_and_tag(self, document_id, tag_id):
        try:
            return self.document_tag_interface.unlink_document_tag(document_id, tag_id)
        
        except (DocumentNotFoundError, TagNotFoundError, DocumentTagNotFoundError) as e:
            raise HTTPException(
                status_code=404,
                detail=f"Unassociation failed: {str(e)}"
            )

        except DocumentTagLinkError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unassociation failed: {str(e)}"
            )
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error unassociating document and tag: {str(e)}"
            ) 

    async def summarize_document_by_document_id(self, document_id: str) -> Summary:
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
        
        except SummaryCreationError as e:
            raise HTTPException(status_code=500, detail=str(e))

        except OpenAIServiceError as e:
            raise HTTPException(status_code=500, detail=str(e))

        except HTTPException as e:
            raise e
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error summarizing document: {str(e)}"
            )
    
    def search_for_documents(self, request):
        try:
            natural_language_query = request.query
            query_embedding = embed_text(natural_language_query)
                
            tags = self.tag_interface.get_similar_tags(query_embedding)

            doc_dict = {}
            for tag in tags:
                for doc in self.get_documents_by_tag_id(str(tag.id)):
                    doc_dict[doc.id] = doc

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
            raise HTTPException(
                status_code=500,
                detail=f"Error searching for similar documents: {str(e)}"
            )
        