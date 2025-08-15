from sqlalchemy import Column, BigInteger, Integer, SmallInteger, Text, Date, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mood_text = Column(Text)  # "오늘은 피곤해요"
    mood_level = Column(SmallInteger, CheckConstraint('mood_level >= 1 AND mood_level <= 5'))
    ritual_suggestion = Column(JSONB)  # AI가 제안한 활동
    ritual_completed = Column(Boolean, default=False)
    checkin_date = Column(Date, nullable=False, server_default=func.current_date())
    
    # 관계 설정
    user = relationship("User", back_populates="daily_checkins")
    
    # 하루에 한 번만 체크인
    __table_args__ = (
        UniqueConstraint('user_id', 'checkin_date', name='_user_checkin_date_uc'),
    )


class HeartTree(Base):
    __tablename__ = "heart_trees"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    growth_level = Column(Integer, nullable=False, default=0, server_default='0')
    last_grew_at = Column(DateTime(timezone=True))
    
    # 관계 설정
    user = relationship("User", back_populates="heart_tree")
    
    __table_args__ = (
        CheckConstraint('growth_level >= 0', name='_growth_level_check'),
    )


class AIPersonaHistory(Base):
    __tablename__ = "ai_persona_histories"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    persona_data = Column(JSONB, nullable=False)  # LLM이 생성한 페르소나 분석
    event_type = Column(String(50))  # 'initial', 'daily_ritual' 등
    event_date = Column(Date, nullable=False, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="persona_histories")