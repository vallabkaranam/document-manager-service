from urllib.parse import urlparse
from fastapi import HTTPException
from sentence_transformers import util
from app.ml_models.embedding_models import shared_sentence_model

from app.utils.document_utils import extract_tags, extract_text_from_pdf, generate_unique_filename


class DocumentController:
    def __init__(self, s3_interface, queue_interface, document_interface):
        self.s3_interface = s3_interface
        self.queue_interface = queue_interface
        self.document_interface = document_interface
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
            raise e
    
    def view_document_by_id(self, document_id):
        # take doc id and get document
        document = self.document_interface.get_document_by_id(document_id)

        # get storage path from doc object
        storage_path = document.storage_path
        # parse
        parsed = urlparse(storage_path)
        key = parsed.path.lstrip("/") 

        # pass that key into generate_presigned_url
        return self.s3_interface.generate_presigned_url(key)
        
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
        
        