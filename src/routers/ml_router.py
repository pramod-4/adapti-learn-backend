from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..schemas import PredictUpdateRequest
import joblib
import pandas as pd
import os

router = APIRouter(prefix="/ml", tags=["ML Detection"])

MODEL_DIR = os.path.join(os.getcwd(), "src", "ml_models")

MODEL_PATHS = {
    "active_reflective": os.path.join(MODEL_DIR, "rf_model_ActiveReflective.pkl"),
    "sensing_intuitive": os.path.join(MODEL_DIR, "rf_model_SensingIntuitive.pkl"),
    "visual_verbal": os.path.join(MODEL_DIR, "rf_model_VisualVerbal.pkl"),
    "sequential_global": os.path.join(MODEL_DIR, "rf_model_SequentialGlobal.pkl"),
}

MODELS = {}

for key, path in MODEL_PATHS.items():
    try:
        loaded = joblib.load(path)
        if isinstance(loaded, dict):
            if "model" in loaded:
                MODELS[key] = loaded["model"]
                print(f"✅ Loaded {key} (model extracted from dict)")
            else:
                MODELS[key] = loaded
                print(f"✅ Loaded {key} (dict structure, used as-is)")
        else:
            MODELS[key] = loaded
            print(f"✅ Loaded {key} (direct model object)")
    except Exception as e:
        print(f"⚠️ Failed to load {key}: {e}")
        MODELS[key] = None


FEATURES = [
    "interaction_count",
    "avg_session_length",
    "time_visual_content",
    "time_text_content",
    "visual_text_ratio",
    "quiz_score_visual",
    "quiz_score_text",
    "navigation_jump_count",
    "reflection_time_avg",
    "content_revisit_rate",
]

@router.post("/predict-update/{user_id}")
def predict_and_update_learning_styles(user_id: int, payload: PredictUpdateRequest, db: Session = Depends(get_db)):
    try:
        df = pd.DataFrame([payload.parameters.model_dump()])  # ✅ Updated for Pydantic v2
        print(df)
        raw_preds = {}
        for style, model in MODELS.items():
            if model is None:
                raw_preds[style] = None
            else:
                try:
                    raw_preds[style] = int(model.predict(df)[0])
                except Exception as e:
                    raw_preds[style] = f"Prediction error: {e}"

        label_map = {
            "active_reflective": {0: "Active", 1: "Reflective"},
            "sensing_intuitive": {0: "Sensing", 1: "Intuitive"},
            "visual_verbal": {0: "Visual", 1: "Verbal"},
            "sequential_global": {0: "Sequential", 1: "Global"},
        }

        readable_preds = {
            k: label_map[k].get(v, "Unknown") if isinstance(v, int) else str(v)
            for k, v in raw_preds.items()
        }

        learner = db.query(models.LearnerProfile).filter(models.LearnerProfile.user_id == user_id).first()
        if not learner:
            raise HTTPException(status_code=404, detail="Learner profile not found")

        learner.active_reflective = readable_preds["active_reflective"]  # type: ignore
        learner.sensing_intuitive = readable_preds["sensing_intuitive"]  # type: ignore
        learner.visual_verbal = readable_preds["visual_verbal"]  # type: ignore
        learner.sequential_global = readable_preds["sequential_global"]  # type: ignore
        learner.parameters = payload.model_dump()  # type: ignore


        db.commit()
        db.refresh(learner)

        return {
            "message": "✅ Learning styles predicted and updated successfully",
            "predicted_learning_styles": readable_preds,
            "updated_profile": {
                "user_id": learner.user_id,
                "active_reflective": learner.active_reflective,
                "sensing_intuitive": learner.sensing_intuitive,
                "visual_verbal": learner.visual_verbal,
                "sequential_global": learner.sequential_global,
                "parameters": learner.parameters or {},
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction/Update error: {str(e)}")


@router.get("/model-info")
def get_model_info():
    info = {}
    for name, model in MODELS.items():
        if model is None:
            info[name] = {"status": "❌ Failed to load"}
        else:
            info[name] = {
                "status": "✅ Loaded",
                "model_type": type(model).__name__,
                "n_features_expected": len(FEATURES),
                "features": FEATURES,
                "has_predict_proba": hasattr(model, "predict_proba"),
            }
    return info
