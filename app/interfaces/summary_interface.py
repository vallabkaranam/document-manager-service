import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.summary import Summary
from app.schemas.summary_schemas import Summary as SummaryPydantic

class SummaryInterface:
    def __init__(self, db: Session):
        self.db = db
    
    def get_summaries_by_document_id(self, document_id: str):
        document_uuid = uuid.UUID(document_id)
        summaries = self.db.query(Summary).filter(Summary.document_id == document_uuid).first()

        if not summaries:
            raise HTTPException(
                status_code=404,
                detail=f"Summaries for document {document_id} not found"
            )

        response = [SummaryPydantic.model_validate(summary) for summary in summaries]

        return response

    def create_summary_by_document_id(self, content: str, document_id: str):
        document_uuid = uuid.UUID(document_id)
        summary = Summary(
            content=content,
            document_id=document_uuid
        )
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)

        return SummaryPydantic.model_validate(summary)

