import asyncio
from sqlalchemy import text
from app.core.database import engine, Base
from app.models import *  # 모든 모델 import


async def init_db():
    """DB 초기화 - 테이블만 생성 (데이터 유지)"""
    async with engine.begin() as conn:
        # 모든 테이블 생성 (이미 있으면 무시)
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


async def reset_db():
    """DB 완전 초기화 - 모든 테이블 삭제 후 재생성 (Spring ddl-auto: create-drop)"""
    async with engine.begin() as conn:
        print("모든 테이블 삭제 중...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("새 테이블 생성 중...")
        await conn.run_sync(Base.metadata.create_all)
        print("DB 초기화 완료!")
        
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
    # 기본 실행: 테이블만 생성 (데이터 유지)
    asyncio.run(init_db())
    
    # 완전 초기화가 필요한 경우 명시적으로 reset_db() 호출
    # asyncio.run(reset_db())