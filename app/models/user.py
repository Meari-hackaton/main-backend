from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    social_provider = Column(String(50), nullable=False)
    social_id = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    nickname = Column(String(100))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
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
    
    # 복합 유니크 제약조건
    __table_args__ = (
        UniqueConstraint('social_provider', 'social_id', name='_social_provider_id_uc'),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    session_id = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    user = relationship("User", back_populates="sessions")