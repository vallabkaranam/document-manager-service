import os
import boto3
from botocore.exceptions import ClientError
import json
from app.schemas.errors import SQSMessageSendError
from typing import Dict

class QueueInterface:
    def __init__(self, queue_url: str = os.getenv("SQS_QUEUE_URL"), region_name: str = os.getenv("AWS_REGION")) -> None:
        self.sqs = boto3.client("sqs", region_name=region_name)
        self.queue_url = queue_url

    def send_document_tagging_message(self, document_id: str, s3_url: str, content_type: str) -> Dict:
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