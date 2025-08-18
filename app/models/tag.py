from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=False)  # 'major' or 'minor'
    parent_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=True)
    order_index = Column(Integer, default=0)  # 정렬 순서
    
    # 관계 설정
    parent = relationship("Tag", remote_side=[id], backref="children")
    news_items = relationship("News", back_populates="tag")