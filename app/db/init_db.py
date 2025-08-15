import asyncio
from sqlalchemy import text
from app.core.database import engine, Base
from app.models import *  # 모든 모델 import


async def init_db():
    async with engine.begin() as conn:
        # 모든 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
        print("테이블 생성 완료")
        
        # 생성된 테이블 확인
        result = await conn.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
        )
        tables = result.fetchall()
        
        print("\n생성된 테이블 목록:")
        for table in tables:
            print(f"  - {table[0]}")


if __name__ == "__main__":
    asyncio.run(init_db())