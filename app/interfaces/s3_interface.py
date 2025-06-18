import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import tempfile

class S3Interface:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

    def upload_file(self, file_obj, filename: str) -> str:
        """
        Uploads a file-like object to S3 and returns the S3 URL path.
        """
        try:
            # Save the file content to a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(file_obj)
                tmp_file_path = tmp_file.name

            # Upload the temporary file to S3
            self.s3_client.upload_file(
                Filename=tmp_file_path,
                Bucket=self.bucket_name,
                Key=filename,
                ExtraArgs={'ACL': 'private'}
            )

            # Clean up the temporary file
            os.remove(tmp_file_path)

            # Return the correct S3 URL format
            region = os.getenv('AWS_REGION', 'us-east-1')
            s3_url = f'https://{self.bucket_name}.s3.{region}.amazonaws.com/{filename}'
            return s3_url
        except (NoCredentialsError, ClientError) as e:
            raise Exception(f"S3 upload failed: {e}") 