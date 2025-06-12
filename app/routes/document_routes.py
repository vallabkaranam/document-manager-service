from fastapi import APIRouter

router = APIRouter()

def upload_document(
        db: Session: Depends(get_db)
) -> DocumentController:


