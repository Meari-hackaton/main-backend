"""
데이터베이스 상태 점검 스크립트
배포 후 실행하여 모든 테이블과 데이터가 정상인지 확인
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine

async def check_db_health():
    """데이터베이스 상태 전체 점검"""
    
    async with engine.begin() as conn:
        print("=" * 60)
        print("🔍 메아리 데이터베이스 상태 점검")
        print("=" * 60)
        
        try:
            # 1. 테이블 존재 확인
            print("\n📋 테이블 상태:")
            tables = [
                'users', 'user_sessions', 'tags', 'news', 'news_quotes',
                'youth_policies', 'meari_sessions', 'generated_cards',
                'rituals', 'heart_trees', 'ai_persona_histories',
                'user_content_histories', 'daily_rituals', 'user_streaks'
            ]
            
            for table in tables:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                exists = result.scalar()
                
                if exists:
                    # 테이블 레코드 수 확인
                    count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    status = "✅" if exists else "❌"
                    print(f"  {status} {table:<25} : {count:>6} rows")
                else:
                    print(f"  ❌ {table:<25} : 테이블 없음")
            
            # 2. Users 테이블 컬럼 확인
            print("\n🔑 Users 테이블 컬럼 상태:")
            columns = ['id', 'email', 'password', 'nickname', 'is_active', 
                      'social_provider', 'social_id', 'created_at']
            
            for col in columns:
                result = await conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = :col
                """), {"col": col})
                
                row = result.first()
                if row:
                    nullable = "NULL가능" if row.is_nullable == 'YES' else "NOT NULL"
                    default = f"(기본값: {row.column_default})" if row.column_default else ""
                    print(f"  ✅ {col:<20} : {row.data_type:<15} {nullable:<10} {default}")
                else:
                    print(f"  ❌ {col:<20} : 컬럼 없음")
            
            # 3. 데이터 통계
            print("\n📊 핵심 데이터 통계:")
            
            # 사용자 통계
            result = await conn.execute(text("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(password) as password_users,
                    COUNT(social_provider) as oauth_users,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users
                FROM users
            """))
            stats = result.first()
            print(f"  👤 사용자:")
            print(f"     - 전체: {stats.total_users}명")
            print(f"     - 자체 로그인: {stats.password_users}명")
            print(f"     - OAuth: {stats.oauth_users}명")
            print(f"     - 활성: {stats.active_users}명")
            
            # 뉴스 데이터
            result = await conn.execute(text("SELECT COUNT(*) FROM news"))
            news_count = result.scalar()
            print(f"  📰 뉴스: {news_count}개")
            
            # 정책 데이터
            result = await conn.execute(text("SELECT COUNT(*) FROM youth_policies"))
            policy_count = result.scalar()
            print(f"  📋 청년정책: {policy_count}개")
            
            # 태그 데이터
            result = await conn.execute(text("SELECT COUNT(*) FROM tags"))
            tag_count = result.scalar()
            print(f"  🏷️ 태그: {tag_count}개")
            
            # 리츄얼 데이터
            result = await conn.execute(text("SELECT COUNT(*) FROM rituals"))
            ritual_count = result.scalar()
            print(f"  🎯 리츄얼: {ritual_count}개")
            
            print("\n" + "=" * 60)
            print("✅ 데이터베이스 점검 완료!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 점검 중 에러 발생: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(check_db_health())