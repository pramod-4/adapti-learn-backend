
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from src.entities.user import Domain
from src.entities.knowledge import ConceptDifficulty


class QueryRequest(BaseModel):
    """Main tutoring query request"""
    query: str = Field(..., description="Student's question or topic")
    domain: Optional[Domain] = Field(None, description="Specific domain filter")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")


class TutoringResponse(BaseModel):
    """Main tutoring system response"""
    content: str = Field(..., description="Generated response content")
    format_type: str = Field(..., description="Response format type")
    difficulty_level: int = Field(..., description="Content difficulty level")
    estimated_read_time: int = Field(..., description="Estimated reading time in minutes")
    follow_up_suggestions: List[str] = Field(default=[], description="Suggested follow-up questions")
    
    # Metadata
    concepts_referenced: List[str] = Field(default=[], description="Concepts covered in response")
    prerequisites: List[str] = Field(default=[], description="Prerequisite concepts")
    related_topics: List[str] = Field(default=[], description="Related topics for exploration")
    
    # System metadata
    response_time: float = Field(..., description="Processing time in seconds")
    model_used: str = Field(..., description="LLM model used")
    confidence_score: Optional[float] = Field(None, description="Response confidence")


class FeedbackRequest(BaseModel):
    """User feedback on system responses"""
    interaction_id: str = Field(..., description="ID of the interaction being rated")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_type: str = Field(..., description="Type of feedback")
    comments: Optional[str] = Field(None, description="Additional comments")


class ProfileResponse(BaseModel):
    """User cognitive profile response"""
    active_vs_passive: float = Field(..., description="Active learning preference (0-1)")
    fast_vs_slow: float = Field(..., description="Learning speed preference (0-1)")
    overview_vs_detailed: float = Field(..., description="Detail preference (0-1)")
    long_vs_short: float = Field(..., description="Response length preference (0-1)")
    confidence: float = Field(..., description="Profile confidence (0-1)")
    interaction_count: int = Field(..., description="Number of interactions")
    learning_style: str = Field(..., description="Interpreted learning style")


class RecommendationsResponse(BaseModel):
    """Learning recommendations response"""
    next_concepts: List[Dict[str, Any]] = Field(default=[], description="Recommended concepts to study")
    study_approach: Dict[str, Any] = Field(default={}, description="Recommended study approach")
    difficulty_adjustment: Dict[str, str] = Field(default={}, description="Difficulty adjustment recommendation")
    learning_path: Dict[str, Any] = Field(default={}, description="Suggested learning path")
    study_schedule: Dict[str, Any] = Field(default={}, description="Optimal study schedule")


class HealthCheckResponse(BaseModel):
    """System health check response"""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: Dict[str, str] = Field(..., description="Component status")
    version: str = Field(..., description="System version")

