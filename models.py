# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    google_2fa_secret = Column(String, nullable=True)
    is_google_2fa_enabled = Column(Boolean, default=False)
    reset_password_token = Column(String, nullable=True)
    reset_password_token_expires = Column(DateTime, nullable=True)
    google_id = Column(String, nullable=True, unique=True)
    line_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_sessions = relationship("ChatSession", back_populates="user")
    reviews = relationship("UserReview", back_populates="user")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True)
    sender = Column(String) # 'user' or 'bot'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
    feedback = relationship("MessageFeedback", back_populates="message", cascade="all, delete-orphan")

class MessageFeedback(Base):
    __tablename__ = "message_feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    feedback_type = Column(String) # 'like' or 'dislike'

    message = relationship("ChatMessage", back_populates="feedback")
    user = relationship("User")

    __table_args__ = (UniqueConstraint('message_id', 'user_id', name='_message_user_uc'),)

class UserReview(Base):
    __tablename__ = "user_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reviews")

class GeneralFeedback(Base):
    __tablename__ = 'general_feedback'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True) # Can be anonymous
    feedback_type = Column(String, nullable=False) # e.g., 'suggestion', 'bug'
    message = Column(Text, nullable=False)
    page_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
