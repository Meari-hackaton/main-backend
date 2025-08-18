from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class News(Base):
    __tablename__ = "news"
    
    news_id = Column(String(50), primary_key=True)  # 빅카인즈 고유 ID
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # 뉴스 본문
    provider = Column(String(100), nullable=False)  # 언론사
    published_at = Column(DateTime(timezone=True), nullable=False)
    link_url = Column(String(500))  # 원문 링크
    category_codes = Column(JSONB)  # 카테고리 코드 리스트 ["003005000", "003007000"]
    tag_id = Column(BigInteger, ForeignKey("tags.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 관계 설정
    tag = relationship("Tag", back_populates="news_items")
    quotes = relationship("NewsQuote", back_populates="news", cascade="all, delete-orphan")


class NewsQuote(Base):
    __tablename__ = "news_quotes"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    news_id = Column(String(50), ForeignKey("news.news_id", ondelete="CASCADE"), nullable=False)
    quote_text = Column(Text, nullable=False)
    quote_type = Column(String(50), nullable=False)  # 'experience', 'emotion', 'insight'
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 관계 설정
    news = relationship("News", back_populates="quotes")