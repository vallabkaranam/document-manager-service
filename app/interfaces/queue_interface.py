"""
Queue Interface Module

Provides an abstraction over AWS SQS operations including sending messages for document tagging jobs.
This interface ensures consistent error handling and encapsulates all SQS-related logic behind a single class.

Key Capabilities:
- Send document tagging messages to SQS
- Ensure validation and exception safety across operations

Assumptions:
- Environment variables SQS_QUEUE_URL and AWS_REGION are configured
- All inputs and outputs are validated
"""

import os
import boto3
from botocore.exceptions import ClientError
import json
from app.schemas.errors import SQSMessageSendError
from typing import Dict

class QueueInterface:
    """
    Provides an abstraction over SQS operations, ensuring consistent error handling
    and encapsulating all SQS-related logic behind a single class.
    """
    def __init__(self, queue_url: str = os.getenv("SQS_QUEUE_URL"), region_name: str = os.getenv("AWS_REGION")) -> None:
        """
        Initializes the SQS interface with a specified queue URL and AWS region.

        Args:
            queue_url (str): The SQS queue URL to interact with.
            region_name (str): The AWS region name.
        """
        self.sqs = boto3.client("sqs", region_name=region_name)
        self.queue_url = queue_url

    def send_document_tagging_message(self, document_id: str, s3_url: str, content_type: str) -> Dict:
        """
        Sends a message to the SQS queue for document tagging.

        Args:
            document_id (str): The document's UUID.
            s3_url (str): The S3 URL of the document.
            content_type (str): The MIME type of the document.

        Returns:
            Dict: The SQS send_message response.

        Raises:
            SQSMessageSendError: If the message sending fails.
        """
        try:
            message_body = {
                "document_id": document_id,
                "s3_url": s3_url,
                "content_type": content_type
            }

            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )
            return response
        except ClientError as e:
            raise SQSMessageSendError(f"Failed to send message to SQS for document_id={document_id}") from e