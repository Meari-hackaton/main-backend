#!/usr/bin/env python
"""
데이터베이스 테이블 생성 스크립트
EC2 서버에서 실행용
"""
import asyncio
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, engine
from app.models.user import User, UserSession
from app.models.card import GeneratedCard
from app.models.ritual import Ritual
from app.models.persona import AIPersonaHistory
from app.models.policy import YouthPolicy
from app.models.news import News, NewsQuote
from app.models.tag import Tag
from app.models.history import UserContentHistory
from app.models.daily import DailyRitual, UserStreak, RitualTemplate

async def init_database():
    """데이터베이스 테이블 생성"""
    async with engine.begin() as conn:
        # 모든 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
        print("✅ 모든 테이블 생성 완료")
        
        # 생성된 테이블 목록 출력
        tables = Base.metadata.tables.keys()
        print(f"📋 생성된 테이블: {', '.join(tables)}")

if __name__ == "__main__":
    asyncio.run(init_database())