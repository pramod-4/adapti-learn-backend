
from typing import Any, Dict, Optional


class TutoringSystemException(Exception):
    """Base exception for the tutoring system"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(TutoringSystemException):
    """Authentication related errors"""
    pass


class AuthorizationError(TutoringSystemException):
    """Authorization related errors"""
    pass


class DatabaseError(TutoringSystemException):
    """Database related errors"""
    pass


class KnowledgeGraphError(TutoringSystemException):
    """Knowledge graph related errors"""
    pass


class CognitiveAnalysisError(TutoringSystemException):
    """Cognitive analysis related errors"""
    pass


class LLMError(TutoringSystemException):
    """LLM related errors"""
    pass


class RateLimitError(TutoringSystemException):
    """Rate limiting errors"""
    pass


class ValidationError(TutoringSystemException):
    """Data validation errors"""
    pass