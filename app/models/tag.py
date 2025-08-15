from sqlalchemy import Column, Integer, String
from app.core.database import Base


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=False)