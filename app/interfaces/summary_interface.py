"""
Summary Interface Module

Encapsulates all business logic for summary-related operations, abstracting the database layer
and providing clean, validated interfaces to the controller and route layers.

Key Capabilities:
- Create and retrieve summaries for documents
- Ensure validation and exception safety across operations

Assumptions:
- Summaries are linked to documents by document_id
- All inputs and outputs are validated Pydantic models
"""

from typing import List
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.summary import Summary
from app.schemas.summary_schemas import Summary as SummaryPydantic
from app.schemas.errors import SummaryCreationError

class SummaryInterface:
    """
    Provides an abstraction over summary operations, ensuring consistent error handling
    and encapsulating all summary-related logic behind a single class.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes the summary interface with a database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def get_summaries_by_document_id(self, document_id: str) -> List[SummaryPydantic]:
        """
        Fetches all summaries for a given document, ordered by creation time (most recent first).

        Args:
            document_id (str): UUID string of the document.

        Returns:
            List[SummaryPydantic]: List of summaries for the document.
        """
        document_uuid = uuid.UUID(document_id)
        summaries = self.db.query(Summary).filter(Summary.document_id == document_uuid).order_by(desc(Summary.created_at)).all()
        response = [SummaryPydantic.model_validate(summary) for summary in summaries]
        return response

    def create_summary_by_document_id(self, document_id: str, content: str) -> SummaryPydantic:
        """
        Creates a new summary for a given document.

        Args:
            document_id (str): UUID string of the document.
            content (str): The summary content.

        Returns:
            SummaryPydantic: The created summary.

        Raises:
            SummaryCreationError: If the summary creation fails.
        """
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

