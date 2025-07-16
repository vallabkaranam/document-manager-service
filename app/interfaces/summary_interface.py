import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.summary import Summary
from app.schemas.summary_schemas import Summary as SummaryPydantic
from app.schemas.errors import SummaryCreationError


class SummaryInterface:
    def __init__(self, db: Session):
        self.db = db
    
    def get_summaries_by_document_id(self, document_id: str):
        document_uuid = uuid.UUID(document_id)
        summaries = self.db.query(Summary).filter(Summary.document_id == document_uuid).order_by(desc(Summary.created_at)).all()

        response = [SummaryPydantic.model_validate(summary) for summary in summaries]

        return response

    def create_summary_by_document_id(self, document_id: str, content: str):
        try:
            document_uuid = uuid.UUID(document_id)
            summary = Summary(
                content=content,
                document_id=document_uuid
            )
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)

            return SummaryPydantic.model_validate(summary)
        
        except Exception as e:
            raise SummaryCreationError(f"Failed to create summary for document {document_id}: {str(e)}") from e

