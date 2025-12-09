from pydantic import BaseModel
from typing import Optional, Literal , List
from datetime import datetime


# ==========================================================
# 1️⃣ USER SCHEMAS
# ==========================================================

class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str  
    active_reflective: Literal["Active", "Reflective"]
    sensing_intuitive: Literal["Sensing", "Intuitive"]
    visual_verbal: Literal["Visual", "Verbal"]
    sequential_global: Literal["Sequential", "Global"]



class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(UserBase):
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True



# ==========================================================
# 2️⃣ LEARNER PROFILE SCHEMAS
# ==========================================================

class ParameterData(BaseModel):
    
    interaction_count: int = 0
    avg_session_length: int = 0
    time_visual_content: int = 0
    time_text_content: int = 0
    visual_text_ratio: float = 0.0
    quiz_score_visual: int = 0
    quiz_score_text: int = 0
    navigation_jump_count: int = 0
    reflection_time_avg: int = 0
    content_revisit_rate: float = 0.0
    theory_practice_ratio: float = 0.0
    
class PredictUpdateRequest(BaseModel):
    active_reflective: str
    sensing_intuitive: str
    visual_verbal: str
    sequential_global: str
    parameters: ParameterData
  

class LearnerProfileBase(BaseModel):
    """Represents the 4 core learning style dimensions + parameters."""
    active_reflective: Literal["Active", "Reflective"]
    sensing_intuitive: Literal["Sensing", "Intuitive"]
    visual_verbal: Literal["Visual", "Verbal"]
    sequential_global: Literal["Sequential", "Global"]
    parameters: ParameterData


class LearnerProfileCreate(LearnerProfileBase):
    user_id: int


class LearnerProfileResponse(LearnerProfileBase):
    profile_id: int
    user_id: int
    last_updated: datetime

    class Config:
        orm_mode = True
        
        
class SessionCognitiveState(BaseModel):
    instruction_flow: Literal[
        "step_by_step",
        "guided",
        "exploratory",
        "high_level"
    ]

    complexity_tolerance: Literal[
        "low",
        "medium",
        "high"
    ]

    pace_preference: Literal[
        "slow",
        "moderate",
        "fast"
    ]

    input_preference: Literal[
        "example_first",
        "theory_first",
        "analogy_based"
    ]

    engagement: Optional[Literal[
        "low",
        "medium",
        "high"
    ]] = None

    confidence: float



# ==========================================================
# 3️⃣ SUBJECT HUB SCHEMAS
# ==========================================================

class SubjectBase(BaseModel):
    title: str
    context: Optional[str] = None


class SubjectCreate(SubjectBase):
    created_by: Optional[int] = None


class SubjectResponse(SubjectBase):
    subject_id: int
    created_at: datetime

    class Config:
        orm_mode = True



# ==========================================================
# 4️⃣ NOTES SCHEMAS
# ==========================================================

class GenerateNotesRequest(BaseModel):
    user_id: int
    subject_id: int


# ==========================================================
# 5️⃣ CHAT HISTORY SCHEMAS
# ==========================================================

class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    user_id: int
    message: str
    history: List[ChatHistoryItem] = []
    subject_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    session_state: SessionCognitiveState



# ==========================================================
# 6️⃣ LEARNING STYLE DETECTION SCHEMAS (ML INTEGRATION)
# ==========================================================

class LearningStyleUpdateRequest(BaseModel):
    """Used by ML model endpoint to update learning style from parameters."""
    user_id: int
    parameters: ParameterData


class LearningStyleUpdateResponse(BaseModel):
    """Returned after recalculating learning styles via ML."""
    user_id: int
    updated_styles: LearnerProfileBase
    message: str = "Learning style updated successfully"
