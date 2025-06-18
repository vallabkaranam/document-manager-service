from fastapi import HTTPException


class DocumentController:
    def __init__(self, s3_interface):
        self.s3_interface = s3_interface

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
            url = self.s3_interface.upload_file(file_content, document_input.filename)
            return url
            
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"S3 upload error: {str(e)}"
            )



        return file, document_input




