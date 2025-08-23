"""
User 테이블에 password와 is_active 컬럼 추가 (배포용)
기존 데이터를 보존하면서 안전하게 마이그레이션
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine

async def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """컬럼 존재 여부 확인"""
    result = await conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = :table_name 
            AND column_name = :column_name
        )
    """), {"table_name": table_name, "column_name": column_name})
    return result.scalar()

async def update_user_table():
    """User 테이블에 새로운 컬럼 추가 - 안전한 마이그레이션"""
    
    async with engine.begin() as conn:
        try:
            # 1. password 컬럼 확인 및 추가
            if not await check_column_exists(conn, "users", "password"):
                await conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN password VARCHAR(255)
                """))
                print("✅ password 컬럼 추가 완료")
            else:
                print("ℹ️ password 컬럼이 이미 존재합니다")
            
            # 2. is_active 컬럼 확인 및 추가
            if not await check_column_exists(conn, "users", "is_active"):
                await conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """))
                print("✅ is_active 컬럼 추가 완료")
            else:
                print("ℹ️ is_active 컬럼이 이미 존재합니다")
            
            # 3. social_provider 컬럼 NOT NULL 제약 확인 및 제거
            # PostgreSQL에서 제약조건 확인
            result = await conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'social_provider'
            """))
            is_nullable = result.scalar()
            
            if is_nullable == 'NO':
                await conn.execute(text("""
                    ALTER TABLE users 
                    ALTER COLUMN social_provider DROP NOT NULL
                """))
                print("✅ social_provider 컬럼을 nullable로 변경")
            else:
                print("ℹ️ social_provider 컬럼이 이미 nullable입니다")
            
            # 4. social_id 컬럼 NOT NULL 제약 확인 및 제거
            result = await conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'social_id'
            """))
            is_nullable = result.scalar()
            
            if is_nullable == 'NO':
                await conn.execute(text("""
                    ALTER TABLE users 
                    ALTER COLUMN social_id DROP NOT NULL
                """))
                print("✅ social_id 컬럼을 nullable로 변경")
            else:
                print("ℹ️ social_id 컬럼이 이미 nullable입니다")
            
            # 5. 기존 사용자 데이터 확인
            result = await conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(password) as with_password,
                       COUNT(social_provider) as with_oauth
                FROM users
            """))
            stats = result.first()
            
            print(f"\n📊 사용자 통계:")
            print(f"  - 전체 사용자: {stats.total}명")
            print(f"  - 자체 로그인 사용자: {stats.with_password}명")
            print(f"  - OAuth 사용자: {stats.with_oauth}명")
            
            print("\n✅ User 테이블 마이그레이션 완료!")
            
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(update_user_table())