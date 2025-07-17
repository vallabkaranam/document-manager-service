"""
Tag Embedding Backfill Script

This standalone script identifies all tags in the database that are missing vector embeddings
and computes them using the shared SentenceTransformer model. It writes the resulting embeddings
to the database and commits the updates in a single batch.

Usage:
    Run this script directly to backfill missing tag embeddings:
        $ python backfill_tag_embeddings.py

Key Capabilities:
- Finds all tags where `embedding` is null
- Encodes tag text using SentenceTransformer
- Updates each tag in-place and commits to the database

Assumptions:
- The Tag model has a nullable `embedding` column
- The embedding is stored as a list[float] and compatible with the DB's vector type
- The SentenceTransformer model is already loaded in memory (via shared import)
"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.tag import Tag
from app.utils.document_utils import embed_text


def backfill_missing_tag_embeddings() -> None:
    """
    Finds and updates all tags without embeddings in the database.
    Embeddings are generated using the shared SentenceTransformer model.
    """
    db: Session = SessionLocal()

    try:
        tags_to_update = db.query(Tag).filter(Tag.embedding == None).all()
        print(f"🔧 Found {len(tags_to_update)} tags with null embeddings.")

        updated = 0
        for tag in tags_to_update:
            if tag.text:
                embedding = embed_text(tag.text)
                tag.embedding = embedding
                updated += 1

        db.commit()
        print(f"✅ Successfully updated {updated} tags with embeddings.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during tag embedding backfill: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_missing_tag_embeddings()