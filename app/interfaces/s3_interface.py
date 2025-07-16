from urllib.parse import urlparse
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import tempfile

class S3UploadError(Exception):
    pass

class S3DownloadError(Exception):
    pass

class S3PresignedUrlError(Exception):
    pass


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
            return f"s3://{self.bucket_name}/{filename}"

        except (NoCredentialsError, ClientError) as e:
            raise S3UploadError(f"Failed to upload file '{filename}' to S3") from e

    def download_file(self, s3_url: str) -> bytes:
        parsed = urlparse(s3_url)

        bucket = parsed.netloc          # "my-bucket"
        key = parsed.path.lstrip("/")   # "folder/filename.pdf"

        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()

        except self.s3_client.exceptions.NoSuchKey as e:
            raise S3DownloadError(f"S3 key '{key}' not found in bucket '{bucket}'") from e

        except (NoCredentialsError, ClientError) as e:
            raise S3DownloadError(f"Failed to download file from S3: {s3_url}") from e

    def generate_presigned_url(self, key: str, expires_in: int = 300) -> str:
        """
        Generates a presigned URL to access a private S3 object.

        Args:
            key (str): The object key in S3 (e.g., 'folder/file.pdf').
            expires_in (int): URL expiration time in seconds (default: 5 minutes).

        Returns:
            str: A presigned URL for downloading the file.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise S3PresignedUrlError(f"Failed to generate presigned URL for key '{key}'") from e