from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class MeariSession(Base):
    __tablename__ = "meari_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    selected_tag_ids = Column(JSONB, nullable=False)  # [1, 5, 12]
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="meari_sessions")
    generated_cards = relationship("GeneratedCard", back_populates="session", cascade="all, delete-orphan")


class GeneratedCard(Base):
    __tablename__ = "generated_cards"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("meari_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    card_type = Column(String(50), nullable=False)  # 'empathy', 'reflection', 'growth' = 공감 , 성찰, 성장
    content = Column(JSONB, nullable=False)  # 카드 내용, 인용문 등 정책 등드ㅡ등
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 관계 설정
    session = relationship("MeariSession", back_populates="generated_cards")
    user = relationship("User", back_populates="generated_cards")