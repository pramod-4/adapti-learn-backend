from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..schemas import GenerateNotesRequest
from ..database import get_db
from .. import models
from ..prompts.os_notes_prompt import BASE_PROMPT, STYLE_PROMPTS
from google import genai
import os
import json

router = APIRouter(
    prefix="/notes",
    tags=["Notes"]
)

try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    raise RuntimeError("Failed to initialize Gemini client. Check GEMINI_API_KEY.") from e


@router.post("/generate")
async def generate_notes(request: GenerateNotesRequest, db: Session = Depends(get_db)):
    try:
        learner = (
            db.query(models.LearnerProfile)
            .filter(models.LearnerProfile.user_id == request.user_id)
            .first()
        )
        if not learner:
            raise HTTPException(status_code=404, detail="Learner profile not found")

        sensing_intuitive = str(getattr(learner, "sensing_intuitive", "") or "").lower()
        active_reflective = str(getattr(learner, "active_reflective", "") or "").lower()

        base_prompt = BASE_PROMPT.strip()
        style_sections = []

        if sensing_intuitive in STYLE_PROMPTS:
            style_sections.append(STYLE_PROMPTS[sensing_intuitive])
        if active_reflective in STYLE_PROMPTS:
            style_sections.append(STYLE_PROMPTS[active_reflective])

        final_prompt = f"{base_prompt}\n\n" + "\n\n".join(style_sections) if style_sections else base_prompt

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_prompt
        )

        raw = json.loads(str(response.text))

        if isinstance(raw, dict) and len(raw) == 1:
            generated = list(raw.values())
        else:
            generated = raw


        subject = (
            db.query(models.SubjectHub)
            .filter(models.SubjectHub.subject_id == request.subject_id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        existing_note = (
            db.query(models.Notes)
            .filter(
                models.Notes.user_id == request.user_id,
                models.Notes.subject_id == request.subject_id
            )
            .order_by(models.Notes.generated_at.desc())
            .first()
        )

        ls = f"{learner.active_reflective},{learner.sequential_global},{learner.sensing_intuitive},{learner.visual_verbal}"

        if existing_note:
            existing_note.content = json.dumps(generated) #type: ignore
            existing_note.learning_style_used = ls #type: ignore
            existing_note.model_version = "gemini-2.5-flash" #type: ignore
            db.commit()
            db.refresh(existing_note)
            return {
                "note_id": existing_note.note_id,
                "generated_notes": generated,
                "message": "Existing note updated successfully"
            }

        new_note = models.Notes(
            user_id=request.user_id,
            subject_id=subject.subject_id,
            content=json.dumps(generated),
            learning_style_used=ls,
            model_version="gemini-2.5-flash"
        )

        db.add(new_note)
        db.commit()
        db.refresh(new_note)

        return {
            "note_id": new_note.note_id,
            "generated_notes": generated,
            "message": "New note created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation or database error: {str(e)}")


@router.get("/{user_id}/{subject}")
async def get_notes_by_subject(user_id: int, subject: str, db: Session = Depends(get_db)):
    try:
        subject_obj = (
            db.query(models.SubjectHub)
            #.filter(models.SubjectHub.title == subject)
            .first()
        )
        if not subject_obj:
            return { "notes": ["subject not found"] }

        notes = (
            db.query(models.Notes)
            .filter(
                models.Notes.user_id == user_id,
                models.Notes.subject_id == subject_obj.subject_id
            )
            .order_by(models.Notes.generated_at.desc())
            .all()
        )

        if not notes:
            return { "notes": ["notes not found"] }

        serialized = [
            {
                "note_id": n.note_id,
                "subject_id": n.subject_id,
                "learning_style_used": n.learning_style_used,
                "model_version": n.model_version,
                "generated_at": n.generated_at,
                "content": (
            lambda c: c[0] if isinstance(c, list) and len(c) == 1 and isinstance(c[0], list) else c
        )(json.loads(n.content))  #type: ignore
            }
            for n in notes
        ]

        return { "notes": serialized }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}")
