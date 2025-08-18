from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=False)  # 'major' or 'minor'
    parent_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=True)
    keywords = Column(JSONB)  # 관련 키워드 리스트 ["번아웃", "직장스트레스", "퇴사"]
    order_index = Column(Integer, default=0)  # 정렬 순서
    
    # 관계 설정
    parent = relationship("Tag", remote_side=[id], backref="children")
    news_items = relationship("News", back_populates="tag")