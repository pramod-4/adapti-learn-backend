
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CognitiveProfile(BaseModel):
    """Student's cognitive learning profile"""
    
    # Core cognitive dimensions (0.0 to 1.0 scale)
    active_vs_passive: float = Field(default=0.5, ge=0.0, le=1.0, 
                                   description="0=passive, 1=active learner")
    fast_vs_slow: float = Field(default=0.5, ge=0.0, le=1.0, 
                              description="0=slow, 1=fast learner")
    overview_vs_detailed: float = Field(default=0.5, ge=0.0, le=1.0, 
                                      description="0=overview, 1=detailed preference")
    long_vs_short: float = Field(default=0.5, ge=0.0, le=1.0, 
                               description="0=short, 1=long responses")
    
    # Meta information
    confidence: float = Field(default=0.1, ge=0.0, le=1.0, 
                            description="Confidence in profile accuracy")
    interaction_count: int = Field(default=0, ge=0, 
                                 description="Number of interactions analyzed")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metrics
    avg_session_duration: Optional[float] = None  # in minutes
    avg_questions_per_session: Optional[float] = None
    preferred_difficulty_level: Optional[int] = Field(default=None, ge=1, le=5)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProfileAnalytics(BaseModel):
    """Analytics data for profile insights"""
    user_id: str
    total_interactions: int
    total_session_time: float  # in minutes
    average_response_time: float  # in seconds
    most_active_domain: Optional[str] = None
    learning_progress: Dict[str, float] = {}  # domain -> progress (0-1)
    engagement_score: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileUpdate(BaseModel):
    """Model for updating cognitive profiles"""
    dimension_updates: Dict[str, float] = {}
    confidence_delta: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = {}

