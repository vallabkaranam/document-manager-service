import os
import time
import json
import boto3
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.interfaces.s3_interface import S3Interface
from app.interfaces.document_interface import DocumentInterface
from app.utils.document_utils import extract_text_from_pdf, extract_tags
from app.ml_models.embedding_models import shared_sentence_model
from sentence_transformers import util

QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION")

sqs = boto3.client("sqs", region_name=AWS_REGION)
s3_interface = S3Interface(os.getenv("S3_BUCKET_NAME"))

def process_message(message_body: dict):
    db: Session = SessionLocal()
    document_interface = DocumentInterface(db)
    model = shared_sentence_model

    try:
        document_id = message_body["document_id"]
        s3_url = message_body["s3_url"]
        content_type = message_body["content_type"]

        # Only tag PDFs for now
        if content_type != "application/pdf":
            print(f"Skipping non-PDF file: {content_type}")
            return

        file_content = s3_interface.download_file(s3_url)
        text = extract_text_from_pdf(file_content)
        tags = extract_tags(text)

        existing_tags = document_interface.get_all_tags()
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

            tag_obj = matched_tag or document_interface.create_tag(tag_text)

            if tag_obj.id not in associated_tag_ids:
                document_interface.link_document_tag(document_id, tag_obj.id)
                associated_tag_ids.add(tag_obj.id)

        print(f"✅ Document {document_id} tagged with {len(associated_tag_ids)} tags.")

    except Exception as e:
        print(f"❌ Error processing message: {str(e)}")

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