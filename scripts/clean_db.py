"""
DB 완전 초기화 스크립트
모든 테이블 CASCADE 삭제
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine


async def clean_database():
    """모든 테이블 CASCADE 삭제"""
    print("=" * 60)
    print("DB 완전 초기화")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # CASCADE로 모든 테이블 삭제
        tables_to_drop = [
            "daily_checkins",  # 옛날 테이블
            "news_quotes",
            "news", 
            "youth_policies",
            "user_content_histories",
            "generated_cards",
            "rituals",
            "heart_trees",
            "ai_persona_histories",
            "meari_sessions",
            "user_sessions",
            "tags",
            "users"
        ]
        
        for table in tables_to_drop:
            try:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"✓ {table} 테이블 삭제")
            except Exception as e:
                print(f"✗ {table} 삭제 실패: {e}")
        
        print("\n모든 테이블 삭제 완료!")
        
        # 남은 테이블 확인
        result = await conn.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
        )
        tables = result.fetchall()
        
        if tables:
            print("\n⚠️ 남은 테이블:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\n✓ DB가 완전히 비었습니다.")


if __name__ == "__main__":
    asyncio.run(clean_database())