from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class NodeResponse(BaseModel):
    name: str
    properties: Dict[str, Any]
    
class TopicWithSubtopicsResponse(BaseModel):
    topic: Optional[NodeResponse]
    subtopics: List[NodeResponse]
    
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    path: Optional[str] = None