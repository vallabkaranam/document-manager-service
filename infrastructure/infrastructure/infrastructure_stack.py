import os
from aws_cdk import (
    Stack,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct

class InfrastructureStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import existing TaggingQueue from ARN (via env var)
        tagging_queue_arn = os.getenv("TAGGING_QUEUE_ARN")
        tagging_queue = sqs.Queue.from_queue_arn(
            self,
            "ImportedTaggingQueue",
            tagging_queue_arn
        )

        # Create new EmbeddingQueue
        embedding_queue = sqs.Queue(
            self,
            "EmbeddingQueue",
            queue_name="EmbeddingQueue"
        )

        # Create EventBridge rule for DocumentReady events
        rule = events.Rule(
            self,
            "DocumentReadyRule",
            event_pattern=events.EventPattern(
                detail_type=["DocumentReady"],
                source=["document-manager-service"]
            )
        )

        # Add both queues as EventBridge targets
        rule.add_target(targets.SqsQueue(tagging_queue))
        rule.add_target(targets.SqsQueue(embedding_queue))