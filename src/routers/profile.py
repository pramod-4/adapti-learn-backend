from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)

@router.put("/update-style/{user_id}")
def update_learning_style(
    user_id: int,
    updated_style: schemas.LearnerProfileBase,
    db: Session = Depends(get_db)
):
    learner_profile = (
        db.query(models.LearnerProfile)
        .filter(models.LearnerProfile.user_id == user_id)
        .first()
    )

    if not learner_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learner profile not found for this user"
        )

    setattr(learner_profile, "active_reflective", updated_style.active_reflective)
    setattr(learner_profile, "sensing_intuitive", updated_style.sensing_intuitive)
    setattr(learner_profile, "visual_verbal", updated_style.visual_verbal)
    setattr(learner_profile, "sequential_global", updated_style.sequential_global)
    setattr(
        learner_profile,
        "parameters",
        updated_style.parameters.dict() if updated_style.parameters else {},
    )

    db.commit()
    db.refresh(learner_profile)

    return {
        "message": "✅ Learning style updated successfully",
        "updated_profile": learner_profile
    }

@router.get("/current-parameters/{user_id}")
def get_current_parameters(user_id: int, db: Session = Depends(get_db)):
    learner = (
        db.query(models.LearnerProfile)
        .filter(models.LearnerProfile.user_id == user_id)
        .first()
    )

    if not learner:
        raise HTTPException(status_code=404, detail="Learner profile not found")

    return {
        "user_id": learner.user_id,
        "active_reflective": learner.active_reflective,
        "sensing_intuitive": learner.sensing_intuitive,
        "visual_verbal": learner.visual_verbal,
        "sequential_global": learner.sequential_global,
        "parameters": learner.parameters or {}
    }
