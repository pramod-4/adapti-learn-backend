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

        if style_sections:
            final_prompt = f"{base_prompt}\n\n" + "\n\n".join(style_sections)
        else:
            final_prompt = base_prompt

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_prompt
        )
        

        return {
            "generated_notes": json.loads(str(response.text))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
