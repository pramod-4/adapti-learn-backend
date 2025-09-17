
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class AcademicLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    GRADUATE = "graduate"
    PROFESSIONAL = "professional"


class Domain(str, Enum):
    OS = "Operating Systems"
    NETWORKING = "Computer Networking"
    DSA = "Data Structures and Algorithms"
    DAA = "Design and Analysis of Algorithms"


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.STUDENT
    is_active: bool = True


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8)
    academic_level: Optional[AcademicLevel] = None
    preferred_domains: Optional[List[Domain]] = []


class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = None
    academic_level: Optional[AcademicLevel] = None
    preferred_domains: Optional[List[Domain]] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """Complete user model"""
    id: str
    academic_level: Optional[AcademicLevel] = None
    preferred_domains: List[Domain] = []
    created_at: datetime
    last_active: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str