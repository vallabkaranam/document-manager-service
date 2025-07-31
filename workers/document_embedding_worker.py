"""
SQS Document Embedding Worker

This module runs a long-lived polling worker that consumes document-embedding requests from an
AWS SQS queue. Each message contains the document ID and metadata. The worker downloads the
document from S3, extracts its text, generates a dense vector embedding using a SentenceTransformer
model, and stores the embedding in the database linked to the corresponding document.

Usage:
    $ python sqs_embedding_worker.py

Key Capabilities:
- Polls SQS for new messages (max 5 at a time)
- Downloads PDF documents from S3
- Extracts text using `PyPDF2`
- Generates embeddings using SentenceTransformer
- Stores document-level embeddings and text to Postgres/pgvector (1 doc = 1 chunk)
- Handles and logs errors gracefully
- Updates document's `embedding_status` field as processing progresses

Assumptions:
- Only `application/pdf` files are embedded
- Worker handles business logic (embedding generation)
- Interfaces handle data access only
- Embeddings are stored in the `document_embeddings` table (dim=384)
- SQS message body is a dict with keys: `detail: { document_id, s3_url, content_type }`
"""

import os
import json
import time
from datetime import datetime, timezone
import boto3
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.document import EmbeddingStatusEnum
from app.schemas.document_schemas import DocumentUpdate
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.document_embedding_interface import DocumentEmbeddingInterface
from app.interfaces.s3_interface import S3Interface, S3DownloadError
from app.ml_models.embedding_models import shared_sentence_model
from app.utils.document_utils import extract_text_from_pdf, embed_text
from app.schemas.errors import DocumentNotFoundError, DocumentUpdateError

QUEUE_URL = os.getenv("EMBEDDING_SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION")

sqs = boto3.client("sqs", region_name=AWS_REGION)
s3_interface = S3Interface(os.getenv("S3_BUCKET_NAME"))


def process_message(message_body: dict) -> None:
    """
    Core business logic for processing a single document embedding request.
    """
    db: Session = SessionLocal()
    document_interface = DocumentInterface(db)
    embedding_interface = DocumentEmbeddingInterface(db)
    model = shared_sentence_model

    try:
        document_id = message_body["document_id"]
        s3_url = message_body["s3_url"]
        content_type = message_body["content_type"]

        # Step 1: Update document status to processing
        try:
            document_interface.update_document(
                document_id,
                DocumentUpdate(
                    embedding_status=EmbeddingStatusEnum.processing,
                    embedding_status_updated_at=datetime.now(timezone.utc),
                ),
            )
        except DocumentNotFoundError as e:
            print(f"❌ Document {document_id} not found: {str(e)}")
            return
        except DocumentUpdateError as e:
            print(f"❌ Failed to update document {document_id} to processing: {str(e)}")

        # Step 2: Skip non-PDFs
        if content_type != "application/pdf":
            print(f"⏭️ Skipping non-PDF document: {content_type}")
            try:
                document_interface.update_document(
                    document_id,
                    DocumentUpdate(
                        embedding_status=EmbeddingStatusEnum.skipped,
                        embedding_status_updated_at=datetime.now(timezone.utc),
                    ),
                )
            except (DocumentNotFoundError, DocumentUpdateError) as e:
                print(f"❌ Failed to mark document as skipped: {str(e)}")
            return

        # Step 3: Download from S3
        try:
            file_content = s3_interface.download_file(s3_url)
        except S3DownloadError as e:
            print(f"❌ S3 download error: {str(e)}")
            try:
                document_interface.update_document(
                    document_id,
                    DocumentUpdate(
                        embedding_status=EmbeddingStatusEnum.failed,
                        embedding_status_updated_at=datetime.now(timezone.utc),
                    ),
                )
            except (DocumentNotFoundError, DocumentUpdateError) as e2:
                print(f"❌ Error marking document as failed: {str(e2)}")
            return

        # Step 4: Extract text
        text = extract_text_from_pdf(file_content)
        if not text.strip():
            print(f"⚠️ Empty PDF text for document {document_id}, skipping.")
            try:
                document_interface.update_document(
                    document_id,
                    DocumentUpdate(
                        embedding_status=EmbeddingStatusEnum.skipped,
                        embedding_status_updated_at=datetime.now(timezone.utc),
                    ),
                )
            except (DocumentNotFoundError, DocumentUpdateError) as e:
                print(f"❌ Error marking empty-text document as skipped: {str(e)}")
            return

        # Step 5: Generate embedding and store in DB
        embedding_vector = embed_text(text)
        embedding_interface.create_chunk_embedding(
            document_id=document_id, 
            embedding_vector=embedding_vector,
            chunk_text=text
            )
        print(f"✅ Stored embedding for document {document_id}.")

        # Step 6: Mark as completed
        try:
            document_interface.update_document(
                document_id,
                DocumentUpdate(
                    embedding_status=EmbeddingStatusEnum.completed,
                    embedding_status_updated_at=datetime.now(timezone.utc),
                ),
            )
        except (DocumentNotFoundError, DocumentUpdateError) as e:
            print(f"❌ Error marking document {document_id} as completed: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected error processing document {message_body.get('document_id')}: {str(e)}")
        try:
            document_interface.update_document(
                message_body.get("document_id"),
                DocumentUpdate(
                    embedding_status=EmbeddingStatusEnum.failed,
                    embedding_status_updated_at=datetime.now(timezone.utc),
                ),
            )
        except (DocumentNotFoundError, DocumentUpdateError) as e2:
            print(f"❌ Error updating document to failed after exception: {str(e2)}")

    finally:
        db.close()


def run_worker():
    """
    Main SQS polling loop. Continuously receives and processes messages.
    """
    print("🟢 SQS Document Embedding Worker started...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10,
            )

            messages = response.get("Messages", [])
            if not messages:
                time.sleep(2)
                continue

            for msg in messages:
                message_body = json.loads(msg["Body"])
                event_detail = message_body.get("detail")

                if not event_detail:
                    print(f"⚠️ Skipping malformed message: {json.dumps(message_body)}")
                    continue

                print(f"📥 Received embedding request: {json.dumps(event_detail)}")
                process_message(event_detail)

                # Delete message after successful processing
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"],
                )

        except Exception as e:
            print(f"Worker loop error: {str(e)}")
        time.sleep(2)


if __name__ == "__main__":
    run_worker()