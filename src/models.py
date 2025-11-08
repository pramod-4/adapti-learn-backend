from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

# ==========================================================
# CONSTANTS FOR FOREIGN KEY REFERENCES
# ==========================================================
USER_FK = "users.user_id"
SUBJECT_FK = "subject_hub.subject_id"


# ==========================================================
# 1️⃣ USERS TABLE
# ==========================================================

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash= Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile = relationship("LearnerProfile", back_populates="user", uselist=False)
    notes = relationship("Notes", back_populates="user")
    chats = relationship("ChatHistory", back_populates="user")
    subjects = relationship("SubjectHub", back_populates="creator")



# ==========================================================
# 2️⃣ LEARNER PROFILE TABLE
# ==========================================================

class LearnerProfile(Base):
    __tablename__ = "learner_profile"

    profile_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_FK, ondelete="CASCADE"), nullable=False)

    active_reflective = Column(String(20), nullable=False)
    sensing_intuitive = Column(String(20), nullable=False)
    visual_verbal = Column(String(20), nullable=False)
    sequential_global = Column(String(20), nullable=False)

    parameters = Column(JSON, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")



# ==========================================================
# 3️⃣ SUBJECT HUB TABLE
# ==========================================================

class SubjectHub(Base):
    __tablename__ = "subject_hub"

    subject_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    context = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey(USER_FK), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    creator = relationship("User", back_populates="subjects")
    notes = relationship("Notes", back_populates="subject")
    chats = relationship("ChatHistory", back_populates="subject")



# ==========================================================
# 4️⃣ NOTES TABLE
# ==========================================================

class Notes(Base):
    __tablename__ = "notes"

    note_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_FK, ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey(SUBJECT_FK, ondelete="CASCADE"), nullable=False)

    content = Column(Text, nullable=False)
    learning_style_used = Column(String(100), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    model_version = Column(String(20), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notes")
    subject = relationship("SubjectHub", back_populates="notes")



# ==========================================================
# 5️⃣ CHAT HISTORY TABLE
# ==========================================================

class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_FK, ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey(SUBJECT_FK, ondelete="CASCADE"), nullable=True)

    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    learning_style_used = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="chats")
    subject = relationship("SubjectHub", back_populates="chats")
