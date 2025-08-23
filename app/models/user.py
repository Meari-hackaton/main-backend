from sqlalchemy import Column, String, DateTime, ForeignKey, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=True)  # nullable for backward compatibility
    nickname = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # OAuth 필드 (하위 호환성 유지)
    social_provider = Column(String(50), nullable=True)
    social_id = Column(String(255), nullable=True)
    
    # 관계 설정
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    meari_sessions = relationship("MeariSession", back_populates="user", cascade="all, delete-orphan")
    generated_cards = relationship("GeneratedCard", back_populates="user", cascade="all, delete-orphan")
    rituals = relationship("Ritual", back_populates="user", cascade="all, delete-orphan")
    content_histories = relationship("UserContentHistory", back_populates="user", cascade="all, delete-orphan")
    heart_tree = relationship("HeartTree", back_populates="user", uselist=False, cascade="all, delete-orphan")
    persona_histories = relationship("AIPersonaHistory", back_populates="user", cascade="all, delete-orphan")
    daily_rituals = relationship("DailyRitual", back_populates="user", cascade="all, delete-orphan")
    user_streak = relationship("UserStreak", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    session_id = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    user = relationship("User", back_populates="sessions")