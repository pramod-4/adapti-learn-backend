from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..utils import hash_password, verify_password
from ..schemas import ParameterData

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_pw = hash_password(user.password)
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    learner_profile = models.LearnerProfile(
        user_id=new_user.user_id,
        active_reflective=user.active_reflective,
        sensing_intuitive=user.sensing_intuitive,
        visual_verbal=user.visual_verbal,
        sequential_global=user.sequential_global,
        parameters=ParameterData().model_dump()  # type: ignore
    )

    db.add(learner_profile)
    db.commit()

    return {
        "message": "✅ User registered successfully",
        "user_id": new_user.user_id,
        "username": new_user.username,
        "learning_style": {
            "active_reflective": user.active_reflective,
            "sensing_intuitive": user.sensing_intuitive,
            "visual_verbal": user.visual_verbal,
            "sequential_global": user.sequential_global
        }
    }



@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, str(db_user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    learner_profile = db.query(models.LearnerProfile).filter(
        models.LearnerProfile.user_id == db_user.user_id
    ).first()

    return {
        "message": "✅ Login successful",
        "user_id": db_user.user_id,
        "username": db_user.username,
        "learning_style": {
            "active_reflective": learner_profile.active_reflective if learner_profile else None,
            "sensing_intuitive": learner_profile.sensing_intuitive if learner_profile else None,
            "visual_verbal": learner_profile.visual_verbal if learner_profile else None,
            "sequential_global": learner_profile.sequential_global if learner_profile else None,
        }
    }
