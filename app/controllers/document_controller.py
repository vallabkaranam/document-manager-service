from fastapi import HTTPException

from app.utils.document_utils import extract_tags, extract_text_from_pdf


class DocumentController:
    def __init__(self, s3_interface, document_interface):
        self.s3_interface = s3_interface
        self.document_interface = document_interface

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

        # Stores file in S3 or local /uploads/ directory
        print(document_input.filename)
        try:
            # Read the file content from the UploadFile object
            file_content = file.file.read()
            # Reset the file pointer to the beginning
            file.file.seek(0)
            # Pass the file content to upload_file
            s3_url = self.s3_interface.upload_file(file_content, document_input.filename)
            # TODO: only allow tagging on pdf for now
            text_from_pdf = extract_text_from_pdf(file_content)
            tags = extract_tags(text_from_pdf)
            return tags



            # Create a document record in the database
            document = self.document_interface.create_document(
                filename=document_input.filename,
                s3_url=s3_url,
                description=document_input.description
            )
            return document
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"S3 upload error: {str(e)}"
            )




