"""
SQS Document Tagging Worker

This module runs a long-lived polling worker that consumes document-tagging requests from an
AWS SQS queue. Each message contains the document ID and metadata. The worker downloads the
document from S3, extracts text, identifies semantic tags using a sentence embedding model,
deduplicates against existing/semantically-similar tags, stores new tags if needed, and links them to the document.

It updates the document's tagging status throughout the lifecycle (processing, completed, failed),
and caches are invalidated if new tags are introduced.

Usage:
    $ python sqs_tagging_worker.py

Key Capabilities:
- Polls SQS for new messages (max 5 at a time)
- Downloads PDF documents from S3
- Extracts text using `PyPDF2`
- Generates tag candidates using KeyBERT-like extractors
- Deduplicates semantically using embedding generation
- Creates new tags (if no match) and links them to the document
- Updates Redis cache if tag space is modified
- Handles and logs errors gracefully
- Updates `tag_status` of each document at each step

Assumptions:
- Only `application/pdf` files are tagged
- Worker handles business logic (embedding generation)
- Interfaces handle data access only
- Redis cache is used with `Cache(redis_client)`
- Tag deduplication threshold is `similarity_score >= 0.5`
- SQS message body is a dict with keys: `detail: { document_id, s3_url, content_type }`
"""

import asyncio
import os
import time
import json
import boto3
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.cache.cache import Cache
from app.cache.redis import redis_client
from app.db.session import SessionLocal
from app.interfaces.s3_interface import S3Interface, S3DownloadError
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.tag_interface import TagInterface
from app.interfaces.document_tag_interface import DocumentTagInterface
from app.schemas.errors import TagCreationError
from app.utils.document_utils import extract_text_from_pdf, extract_tags, embed_text
from app.db.models.document import TagStatusEnum
from app.schemas.document_schemas import DocumentUpdate
from app.schemas.errors import DocumentNotFoundError, DocumentUpdateError

QUEUE_URL = os.getenv("TAGGING_SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION")

sqs = boto3.client("sqs", region_name=AWS_REGION)
s3_interface = S3Interface(os.getenv("S3_BUCKET_NAME"))


def process_message(message_body: dict) -> None:
    """
    Core business logic for processing a single document tagging request.
    """
    db: Session = SessionLocal()
    document_interface = DocumentInterface(db)
    tag_interface = TagInterface(db)
    document_tag_interface = DocumentTagInterface(db)
    cache = Cache(redis_client)

    try:
        document_id = message_body["document_id"]
        s3_url = message_body["s3_url"]
        content_type = message_body["content_type"]

        # Step 1: Set status to processing
        try:
            document_interface.update_document(
                document_id,
                DocumentUpdate(tag_status=TagStatusEnum.processing, tag_status_updated_at=datetime.now(timezone.utc))
            )
        except DocumentNotFoundError as e:
            print(f"❌ Error setting document {document_id} to processing (not found): {str(e)}")
            return
        except DocumentUpdateError as e:
            print(f"❌ Error setting document {document_id} to processing: {str(e)}")

        # Step 2: Skip non-PDFs
        if content_type != "application/pdf":
            print(f"⏭️ Skipping non-PDF file: {content_type}")
            try:
                document_interface.update_document(
                    document_id,
                    DocumentUpdate(tag_status=TagStatusEnum.skipped, tag_status_updated_at=datetime.now(timezone.utc))
                )
            except (DocumentNotFoundError, DocumentUpdateError) as e:
                print(f"❌ Error marking non-PDF document as skipped: {str(e)}")
            return

        # Step 3: Download from S3
        try:
            file_content = s3_interface.download_file(s3_url)
        except S3DownloadError as e:
            print(f"❌ S3 download error: {str(e)}")
            try:
                document_interface.update_document(
                    document_id,
                    DocumentUpdate(tag_status=TagStatusEnum.failed, tag_status_updated_at=datetime.now(timezone.utc))
                )
            except (DocumentNotFoundError, DocumentUpdateError) as e2:
                print(f"❌ Error marking document as failed after S3 error: {str(e2)}")
            return

        # Step 4: Text extraction and tag generation
        text = extract_text_from_pdf(file_content)
        tags = extract_tags(text)

        # Process each extracted tag to check for semantic duplicates
        associated_tag_ids = set()
        new_tag_created = False  # track whether any new tag was created

        for tag_text in tags:
            # Generate embedding for similarity comparison
            tag_embedding = embed_text(tag_text)
            similar_tags = tag_interface.get_similar_tags(tag_embedding, top_k=1)
            
            matched_similar_tag = None
            if similar_tags and similar_tags[0].similarity_score >= 0.5:
                matched_similar_tag = similar_tags[0]

            if matched_similar_tag:
                # Use the existing tag (SimilarTag is a subclass of Tag)
                tag_obj = matched_similar_tag
            else:
                try:
                    # Create a new tag
                    tag_obj = tag_interface.create_tag(tag_text, tag_embedding)
                    new_tag_created = True
                except TagCreationError as e:
                    print(f"⚠️ Failed to create tag '{tag_text}': {str(e)}")
                    continue  # Skip this tag and move to the next one

            # Link the tag to the document (avoid duplicate links)
            # tag_obj can be either SimilarTag (existing) or Tag (new), both have .id
            if tag_obj.id not in associated_tag_ids:
                document_tag_interface.link_document_tag(document_id, str(tag_obj.id))
                associated_tag_ids.add(tag_obj.id)

        if new_tag_created:
            cache.delete("tags:all")

        print(f"✅ Document {document_id} tagged with {len(associated_tag_ids)} tags.")

        # Step 7: Final status update
        try:
            document_interface.update_document(
                document_id,
                DocumentUpdate(tag_status=TagStatusEnum.completed, tag_status_updated_at=datetime.now(timezone.utc))
            )
        except (DocumentNotFoundError, DocumentUpdateError) as e:
            print(f"❌ Error marking document {document_id} as completed: {str(e)}")

    except Exception as e:
        print(f"❌ Error processing message: {str(e)}")
        try:
            document_interface.update_document(
                message_body.get("document_id"),
                DocumentUpdate(tag_status=TagStatusEnum.failed, tag_status_updated_at=datetime.now(timezone.utc))
            )
        except (DocumentNotFoundError, DocumentUpdateError) as e2:
            print(f"❌ Error updating document status to failed: {str(e2)}")

    finally:
        db.close()


def run_worker():
    """
    Main SQS polling loop. Continuously receives and processes messages.
    """
    print("🟢 SQS Document Tagging Worker started...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10
            )

            messages = response.get("Messages", [])
            if not messages:
                continue

            for msg in messages:
                message_body = json.loads(msg["Body"])
                event_detail = message_body.get("detail")

                if not event_detail:
                    print(f"⚠️ Skipping malformed message: {json.dumps(message_body)}")
                    continue

                print(f"📥 Received message: {json.dumps(event_detail)}")
                process_message(event_detail)

                # Delete message from queue after successful processing
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )

        except Exception as e:
            print(f"Worker error: {str(e)}")
        time.sleep(2)


if __name__ == "__main__":
    run_worker()