from fastapi import HTTPException
from sentence_transformers import util
from app.ml_models.embedding_models import shared_sentence_model

from app.utils.document_utils import extract_tags, extract_text_from_pdf, generate_unique_filename


class DocumentController:
    def __init__(self, s3_interface, document_interface):
        self.s3_interface = s3_interface
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
                filename=document_input.filename,
                s3_url=s3_url,
                content_type=file.content_type,
                size=file.size,
                description=document_input.description
            )

            # Only perform auto-tagging for PDF files
            if file.content_type == "application/pdf":
                # TODO: only allow tagging on pdf for now
                # Note: Currently, auto-tagging is limited to PDF files because:
                # 1. extract_text_from_pdf() function only handles PDF extraction
                # 2. To support other file types (images, Word docs, etc.), we would need:
                #    - OCR capabilities for images (e.g., using pytesseract)
                #    - Text extraction for Word docs (e.g., using python-docx)
                #    - A more generic text extraction function that detects file type
                text_from_pdf = extract_text_from_pdf(file_content)
                tags = extract_tags(text_from_pdf)

                # Fetch existing tags from DB
                existing_tags = self.document_interface.get_all_tags()
                existing_texts = [tag.text for tag in existing_tags]

                # tags (existing and new) associated with current document
                associated_tags = []
                associated_tag_ids = set()

                # Encode existing tags only once
                if existing_texts:
                    existing_embeddings = self.model.encode(existing_texts, convert_to_tensor=True)

                for tag_text in tags:
                    matched_tag = None

                    # find if there is an existing_tag that semantically is similar to the tag
                    if existing_texts:
                        query_embedding = self.model.encode(tag_text, convert_to_tensor=True)
                        scores = util.pytorch_cos_sim(query_embedding, existing_embeddings)[0]
                        best_idx = scores.argmax().item()
                        best_score = scores[best_idx].item()
                        if best_score >= 0.5:
                            matched_tag = existing_tags[best_idx]

                    # if so, then use the matched_tag
                    if matched_tag:
                        tag_obj = matched_tag
                    else:
                        # if not then create new tag
                        tag_obj = self.document_interface.create_tag(tag_text)

                    # Avoid duplicate links
                    if tag_obj.id not in associated_tag_ids:
                        # Link tag to document
                        self.document_interface.link_document_tag(document.id, tag_obj.id)
                        associated_tags.append(tag_obj)
                        associated_tag_ids.add(tag_obj.id)
            else:
                # For non-PDF files, return empty list of tags
                associated_tags = []
        
            return document,associated_tags

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
        
        