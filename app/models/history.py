from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserContentHistory(Base):
    __tablename__ = "user_content_histories"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_type = Column(String(50), nullable=False)  # 'policy', 'news', 'quote'
    content_id = Column(String(100), nullable=False)  # policy_id, news_id 등
    viewed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="content_histories")
    
    # 중복 방지: 같은 사용자가 같은 콘텐츠를 중복으로 기록하지 않음
    __table_args__ = (
        UniqueConstraint('user_id', 'content_type', 'content_id', name='_user_content_uc'),
    )