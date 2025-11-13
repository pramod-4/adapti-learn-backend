from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..schemas import SubjectCreate, SubjectResponse

router = APIRouter(
    prefix="/subjects",
    tags=["Subjects"]
)

@router.post("/create", response_model=SubjectResponse)
async def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    # Check for duplicates
    existing = (
        db.query(models.SubjectHub)
        .filter(models.SubjectHub.title == payload.title)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Subject already exists")

    # Create subject instance
    new_subject = models.SubjectHub(
        title=payload.title,
        context=payload.context,
        created_by=payload.created_by   # user_id here
        # created_at by DB automatically
    )

    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)

    return new_subject
