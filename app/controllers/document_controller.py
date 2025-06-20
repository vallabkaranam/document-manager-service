from fastapi import HTTPException
from sentence_transformers import util
from app.ml_models.embedding_models import shared_sentence_model

from app.schemas.document_schemas import Document, Tag, UploadDocumentResponse
from app.utils.document_utils import extract_tags, extract_text_from_pdf


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

            # Pass the file content to upload_file
            s3_url = self.s3_interface.upload_file(file_content, document_input.filename)

            # Create a document record in the database
            document = self.document_interface.create_document(
                filename=document_input.filename,
                s3_url=s3_url,
                description=document_input.description
            )

            # TODO: only allow tagging on pdf for now
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

            document_response = Document(
                id=document.id,
                filename=document.filename,
                storage_path=document.storage_path,
                upload_time=document.upload_time,
                description=document.description,
                user_id=document.user_id
            )

            tags_response = [Tag(id=tag.id, text=tag.text, created_at=tag.created_at) for tag in associated_tags]
        

            return UploadDocumentResponse(
                document=document_response,
                tags=tags_response
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"S3 upload error: {str(e)}"
            )