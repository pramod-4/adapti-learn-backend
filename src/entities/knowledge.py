
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from src.entities.user import Domain


class ConceptDifficulty(int, Enum):
    BEGINNER = 1
    NOVICE = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class RelationType(str, Enum):
    PREREQUISITE_FOR = "prerequisite_for"
    DEPENDS_ON = "depends_on" 
    EXAMPLE_OF = "example_of"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    IMPLEMENTS = "implements"
    USES = "uses"


class ConceptNode(BaseModel):
    """Knowledge graph concept node"""
    concept_id: str = Field(..., description="Unique concept identifier")
    concept_name: str = Field(..., description="Human-readable concept name")
    domain: Domain = Field(..., description="Subject domain")
    difficulty_level: ConceptDifficulty = Field(..., description="Concept difficulty")
    description: str = Field(..., description="Concept description")
    
    # Optional attributes
    keywords: List[str] = Field(default=[], description="Associated keywords")
    learning_objectives: List[str] = Field(default=[], description="Learning objectives")
    examples: List[str] = Field(default=[], description="Code/text examples")
    resources: List[str] = Field(default=[], description="Learning resources")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class ConceptRelation(BaseModel):
    """Relationship between concepts"""
    from_concept: str = Field(..., description="Source concept ID")
    to_concept: str = Field(..., description="Target concept ID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength")
    metadata: Dict[str, Any] = Field(default={}, description="Additional relationship data")
    
    class Config:
        use_enum_values = True


class LearningPath(BaseModel):
    """Structured learning path through concepts"""
    path_id: str
    path_name: str
    domain: Domain
    target_level: ConceptDifficulty
    concept_sequence: List[str] = Field(..., description="Ordered list of concept IDs")
    estimated_duration: Optional[int] = Field(None, description="Estimated hours to complete")
    prerequisites: List[str] = Field(default=[], description="Required prior knowledge")
    
    class Config:
        use_enum_values = True


class SearchQuery(BaseModel):
    """Knowledge graph search query"""
    query_text: str
    domain_filter: Optional[Domain] = None
    difficulty_filter: Optional[ConceptDifficulty] = None
    limit: int = Field(default=10, ge=1, le=50)
    include_related: bool = Field(default=True)


class SearchResult(BaseModel):
    """Knowledge graph search result"""
    concept: ConceptNode
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_type: str  # "name", "description", "keyword"
    related_concepts: List[ConceptNode] = []
    prerequisites: List[ConceptNode] = []
