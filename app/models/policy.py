from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base


class YouthPolicy(Base):
    __tablename__ = "youth_policies"
    
    policy_id = Column(String(50), primary_key=True)  # 청년정책 고유 ID
    policy_name = Column(String(500), nullable=False)
    support_content = Column(Text, nullable=False)  # 지원 내용 상세
    application_url = Column(String(500))  # 신청 URL
    organization = Column(String(200), nullable=False)  # 운영 기관
    target_age = Column(String(100))  # 대상 연령 (예: "19세~34세")
    target_desc = Column(Text)  # 대상 설명
    support_scale = Column(String(200))  # 지원 규모
    application_period = Column(String(200))  # 신청 기간
    tags = Column(ARRAY(BigInteger))  # 관련 태그 ID 리스트
    embedding_id = Column(String(100))  # Milvus 벡터 검색용 ID
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())