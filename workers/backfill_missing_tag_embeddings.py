from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.tag import Tag
from app.utils.document_utils import embed_text

def backfill_missing_tag_embeddings():
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
        print(f"✅ Updated {updated} tags with embeddings.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during backfill: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_missing_tag_embeddings()