import os
import time
import json
import boto3
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.interfaces.s3_interface import S3Interface
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.tag_interface import TagInterface
from app.interfaces.document_tag_interface import DocumentTagInterface
from app.utils.document_utils import extract_text_from_pdf, extract_tags
from app.ml_models.embedding_models import shared_sentence_model
from sentence_transformers import util
from app.db.models.document import TagStatusEnum
from datetime import datetime, timezone 
from app.schemas.document_schemas import DocumentUpdate

QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION")

sqs = boto3.client("sqs", region_name=AWS_REGION)
s3_interface = S3Interface(os.getenv("S3_BUCKET_NAME"))

def process_message(message_body: dict):
    db: Session = SessionLocal()
    document_interface = DocumentInterface(db)
    tag_interface = TagInterface(db)
    document_tag_interface = DocumentTagInterface(db)
    model = shared_sentence_model

    try:
        document_id = message_body["document_id"]
        s3_url = message_body["s3_url"]
        content_type = message_body["content_type"]

        # Set status to processing
        document_interface.update_document(document_id, DocumentUpdate(tag_status=TagStatusEnum.processing, tag_status_updated_at=datetime.now(timezone.utc)))

        # Only tag PDFs for now
        if content_type != "application/pdf":
            print(f"Skipping non-PDF file: {content_type}")
            # Set status to skipped
            document_interface.update_document(document_id, DocumentUpdate(tag_status=TagStatusEnum.skipped, tag_status_updated_at=datetime.now(timezone.utc)))
            return

        file_content = s3_interface.download_file(s3_url)
        text = extract_text_from_pdf(file_content)
        tags = extract_tags(text)

        existing_tags = tag_interface.get_all_tags()
        existing_texts = [tag.text for tag in existing_tags]
        associated_tag_ids = set()

        if existing_texts:
            existing_embeddings = model.encode(existing_texts, convert_to_tensor=True)

        for tag_text in tags:
            matched_tag = None
            if existing_texts:
                query_embedding = model.encode(tag_text, convert_to_tensor=True)
                scores = util.pytorch_cos_sim(query_embedding, existing_embeddings)[0]
                best_idx = scores.argmax().item()
                best_score = scores[best_idx].item()
                if best_score >= 0.5:
                    matched_tag = existing_tags[best_idx]

            tag_obj = matched_tag or tag_interface.create_tag(tag_text)

            if tag_obj.id not in associated_tag_ids:
                document_tag_interface.link_document_tag(str(document_id), str(tag_obj.id))
                associated_tag_ids.add(tag_obj.id)

        print(f"✅ Document {document_id} tagged with {len(associated_tag_ids)} tags.")
        # Set status to completed and tag_status_updated_at to now (UTC)
        document_interface.update_document(
            document_id,
            DocumentUpdate(tag_status=TagStatusEnum.completed, tag_status_updated_at=datetime.now(timezone.utc))
        )

    except Exception as e:
        print(f"❌ Error processing message: {str(e)}")
        # Set status to failed
        try:
            document_interface.update_document(document_id, DocumentUpdate(tag_status=TagStatusEnum.failed, tag_status_updated_at=datetime.now(timezone.utc)))
        except Exception as inner_e:
            print(f"❌ Error updating document status to failed: {str(inner_e)}")

    finally:
        db.close()

def run_worker():
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
                process_message(message_body)

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