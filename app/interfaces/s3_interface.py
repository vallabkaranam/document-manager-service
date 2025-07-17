"""
S3 Interface Module

Provides an abstraction over AWS S3 operations including upload, download,
and generation of presigned URLs. This interface ensures consistent error
handling and encapsulates all S3-related logic behind a single class.

Key Capabilities:
- Upload byte stream to a specific S3 bucket and return its S3 path
- Download objects from S3 using s3:// URLs
- Generate presigned URLs for secure, temporary access to private files

Assumptions:
- Environment variables AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION are configured
- Files are stored privately with ACL='private'
- Presigned URLs are typically valid for 5 minutes unless overridden
"""

from urllib.parse import urlparse
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import tempfile
from app.schemas.errors import S3UploadError, S3DownloadError, S3PresignedUrlError


class S3Interface:
    def __init__(self, bucket_name: str) -> None:
        """
        Initializes the S3 interface with a specified bucket name and AWS credentials.

        Args:
            bucket_name (str): The name of the S3 bucket to interact with.
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

    def upload_file(self, file_obj: bytes, filename: str) -> str:
        """
        Uploads a file (provided as raw bytes) to S3 and returns its S3 URI.

        Args:
            file_obj (bytes): File content in bytes.
            filename (str): Desired S3 key name (e.g., 'folder/file.pdf').

        Returns:
            str: Full S3 URI of the uploaded file (e.g., s3://bucket/key).

        Raises:
            S3UploadError: If the file upload fails due to credentials or client error.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(file_obj)
                tmp_file_path = tmp_file.name

            self.s3_client.upload_file(
                Filename=tmp_file_path,
                Bucket=self.bucket_name,
                Key=filename,
                ExtraArgs={'ACL': 'private'}
            )

            os.remove(tmp_file_path)
            return f"s3://{self.bucket_name}/{filename}"

        except (NoCredentialsError, ClientError) as e:
            raise S3UploadError(f"Failed to upload file '{filename}' to S3") from e

    def download_file(self, s3_url: str) -> bytes:
        """
        Downloads a file from S3 using an s3:// URL.

        Args:
            s3_url (str): The full S3 URL (e.g., s3://bucket/key).

        Returns:
            bytes: The file contents.

        Raises:
            S3DownloadError: If the file is not found or if download fails.
        """
        parsed = urlparse(s3_url)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")

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
            expires_in (int): URL expiration time in seconds (default: 300 seconds).

        Returns:
            str: A presigned URL for downloading the file.

        Raises:
            S3PresignedUrlError: If the presigned URL generation fails.
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