"""
EventBridge Interface Module

Provides an abstraction over AWS EventBridge operations including emitting document processing events.
This interface decouples services by using event-based communication and allows automatic fan-out to consumers like SQS queues.

Key Capabilities:
- Emit a 'DocumentReady' event to EventBridge
- Ensure validation and exception safety across operations

Assumptions:
- Environment variable AWS_REGION is configured
- The EventBridge rule is set up to route 'DocumentReady' events to one or more targets (e.g., SQS queues)
- EventBus is 'default' unless otherwise specified
"""

import os
import boto3
from botocore.exceptions import ClientError
import json
from app.schemas.errors import EventBridgeEmitError
from typing import Dict

class EventBridgeInterface:
    """
    Provides an abstraction over EventBridge operations, ensuring consistent error handling
    and encapsulating all event-related logic behind a single class.
    """
    def __init__(self, region_name: str = os.getenv("AWS_REGION"), event_bus_name: str = "default") -> None:
        """
        Initializes the EventBridge interface with a specified AWS region and EventBus name.

        Args:
            region_name (str): The AWS region name.
            event_bus_name (str): The EventBridge bus name (default is "default").
        """
        self.client = boto3.client("events", region_name=region_name)
        self.event_bus_name = event_bus_name

    def emit_document_ready_event(self, document_id: str, s3_url: str, content_type: str) -> Dict:
        """
        Emits a 'DocumentReady' event to EventBridge with document metadata.

        Args:
            document_id (str): The UUID of the document.
            s3_url (str): The S3 URL where the document is stored.
            content_type (str): The MIME type of the document.

        Returns:
            Dict: The EventBridge put_events response.

        Raises:
            EventBridgeEmitError: If event emission fails.
        """
        try:
            event_detail = {
                "document_id": document_id,
                "s3_url": s3_url,
                "content_type": content_type
            }

            response = self.client.put_events(
                Entries=[
                    {
                        "Source": "document-manager-service",
                        "DetailType": "DocumentReady",
                        "Detail": json.dumps(event_detail),
                        "EventBusName": self.event_bus_name
                    }
                ]
            )
            return response
        except ClientError as e:
            raise EventBridgeEmitError(f"Failed to emit DocumentReady event for document_id={document_id}") from e 