from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class DailyRitual(Base):
    """일일 리츄얼 활동 관리"""
    __tablename__ = "daily_rituals"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, server_default=func.current_date())
    
    # 리츄얼 정보 (GrowthAgent의 experience 카드에서 생성)
    ritual_title = Column(String(200), nullable=False)
    ritual_description = Column(Text)
    ritual_type = Column(String(50))  # meditation, exercise, diary, reading, etc.
    duration_minutes = Column(Integer, default=10)  # 예상 소요 시간
    
    # 완료 상태
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))
    
    # 사용자 피드백 (완료 시)
    user_note = Column(Text)  # "명상 후 마음이 편안해졌어요"
    user_mood = Column(String(50))  # happy, calm, tired, energetic
    difficulty_rating = Column(Integer)  # 1-5 난이도
    
    # 관계
    user = relationship("User", back_populates="daily_rituals")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='_user_daily_ritual_uc'),
    )


class UserStreak(Base):
    """사용자 연속 활동 추적"""
    __tablename__ = "user_streaks"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # 연속 기록
    current_streak = Column(Integer, nullable=False, default=0)  # 현재 연속 일수
    longest_streak = Column(Integer, nullable=False, default=0)  # 최장 연속 일수
    
    # 전체 통계
    total_days_active = Column(Integer, nullable=False, default=0)  # 총 활동 일수
    total_rituals_completed = Column(Integer, nullable=False, default=0)  # 총 완료 리츄얼
    total_rituals_created = Column(Integer, nullable=False, default=0)  # 총 생성 리츄얼
    
    # 최근 활동
    last_activity_date = Column(Date)
    last_ritual_date = Column(Date)
    
    # 업데이트 타임스탬프
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 관계
    user = relationship("User", back_populates="streak", uselist=False)


class RitualTemplate(Base):
    """리츄얼 템플릿 (재사용 가능한 리츄얼)"""
    __tablename__ = "ritual_templates"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 템플릿 정보
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    duration_minutes = Column(Integer, default=10)
    difficulty_level = Column(String(20), default="easy")  # easy, medium, hard
    
    # 카테고리/태그
    category = Column(String(50))  # 마음건강, 신체활동, 창의활동 등
    tags = Column(Text)  # comma-separated tags
    
    # 추천 대상
    recommended_for_tags = Column(Text)  # 추천 태그 ID 리스트 (comma-separated)
    
    # 활성화 상태
    is_active = Column(Boolean, default=True)
    
    # 사용 통계
    usage_count = Column(Integer, default=0)
    avg_rating = Column(Integer)  # 1-5
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())