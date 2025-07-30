import os
from dotenv import load_dotenv
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput,
    RemovalPolicy,
    Tags,
)
from constructs import Construct

# Load environment variables
load_dotenv()

class InfrastructureStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Read from .env
        bucket_name = os.getenv("S3_BUCKET_NAME", "document-manager-service-bucket")
        tagging_queue_name = os.getenv("TAGGING_SQS_QUEUE_URL").split("/")[-1]
        embedding_queue_name = os.getenv("EMBEDDING_SQS_QUEUE_URL").split("/")[-1]

        # ✅ S3 bucket
        document_bucket = s3.Bucket(
            self,
            "DocumentManagerBucket",
            bucket_name=bucket_name,
            versioned=True,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # ✅ SQS queues
        tagging_queue = sqs.Queue(
            self,
            "TaggingQueue",
            queue_name=tagging_queue_name,
        )

        embedding_queue = sqs.Queue(
            self,
            "EmbeddingQueue",
            queue_name=embedding_queue_name,
        )

        # ✅ EventBridge rule for "DocumentReady"
        document_ready_rule = events.Rule(
            self,
            "DocumentReadyRule",
            event_pattern=events.EventPattern(
                source=["document-manager-service"],
                detail_type=["DocumentReady"],
            ),
        )

        # ✅ Connect queues to EventBridge rule
        document_ready_rule.add_target(targets.SqsQueue(tagging_queue))
        document_ready_rule.add_target(targets.SqsQueue(embedding_queue))

        # ✅ Outputs for visibility
        CfnOutput(self, "S3BucketName", value=document_bucket.bucket_name)
        CfnOutput(self, "TaggingQueueURL", value=tagging_queue.queue_url)
        CfnOutput(self, "EmbeddingQueueURL", value=embedding_queue.queue_url)

        # ✅ Tags
        Tags.of(self).add("Project", "DocumentManager")
        Tags.of(self).add("Environment", "Production")