"""
데이터베이스 테이블별 데이터 확인 스크립트
"""
import asyncio
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 동기 연결 설정
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_all_tables():
    """모든 테이블의 데이터 개수 확인"""
    
    print("\n" + "="*60)
    print("📊 데이터베이스 테이블별 데이터 현황")
    print("="*60)
    
    with SessionLocal() as session:
        # 모든 테이블 정보 조회
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = session.execute(tables_query).fetchall()
        
        # 테이블 분류
        user_tables = []      # 유저 관련 (삭제 대상)
        collected_tables = [] # 수집 데이터 (보존 대상)
        system_tables = []    # 시스템 테이블
        
        for (table_name,) in tables:
            # 각 테이블의 행 개수 조회
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            count = session.execute(count_query).scalar()
            
            # 테이블 분류
            if table_name in ['users', 'user_sessions', 'meari_sessions', 'generated_cards', 
                              'rituals', 'heart_trees', 'ai_persona_histories', 
                              'user_content_histories', 'daily_rituals', 'user_streaks']:
                user_tables.append((table_name, count))
            elif table_name in ['news', 'news_quotes', 'youth_policies', 'tags']:
                collected_tables.append((table_name, count))
            elif table_name in ['ritual_templates', 'alembic_version']:
                system_tables.append((table_name, count))
            else:
                system_tables.append((table_name, count))
        
        # 결과 출력
        print("\n🗑️  유저 관련 테이블 (삭제 대상)")
        print("-" * 40)
        total_user_data = 0
        for table_name, count in user_tables:
            print(f"  {table_name:30} : {count:,} 행")
            total_user_data += count
        print(f"  {'총 유저 데이터':30} : {total_user_data:,} 행")
        
        print("\n💾 수집 데이터 테이블 (보존 대상)")
        print("-" * 40)
        total_collected_data = 0
        for table_name, count in collected_tables:
            print(f"  {table_name:30} : {count:,} 행")
            total_collected_data += count
        print(f"  {'총 수집 데이터':30} : {total_collected_data:,} 행")
        
        print("\n⚙️  시스템 테이블")
        print("-" * 40)
        for table_name, count in system_tables:
            print(f"  {table_name:30} : {count:,} 행")
        
        # 중요 데이터 상세 확인
        print("\n" + "="*60)
        print("📌 중요 수집 데이터 상세")
        print("="*60)
        
        # 뉴스 데이터
        news_count = session.execute(text("SELECT COUNT(*) FROM news")).scalar()
        quotes_count = session.execute(text("SELECT COUNT(*) FROM news_quotes")).scalar()
        policies_count = session.execute(text("SELECT COUNT(*) FROM youth_policies")).scalar()
        tags_count = session.execute(text("SELECT COUNT(*) FROM tags")).scalar()
        
        print(f"\n✅ 보존될 데이터:")
        print(f"  - 뉴스 기사: {news_count:,}개")
        print(f"  - 뉴스 인용문: {quotes_count:,}개")
        print(f"  - 청년 정책: {policies_count:,}개")
        print(f"  - 태그: {tags_count:,}개")
        
        # 유저 데이터 확인
        user_count = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
        session_count = session.execute(text("SELECT COUNT(*) FROM user_sessions")).scalar()
        card_count = session.execute(text("SELECT COUNT(*) FROM generated_cards")).scalar()
        ritual_count = session.execute(text("SELECT COUNT(*) FROM rituals")).scalar()
        
        print(f"\n❌ 삭제될 데이터:")
        print(f"  - 사용자: {user_count:,}명")
        print(f"  - 세션: {session_count:,}개")
        print(f"  - 생성된 카드: {card_count:,}개")
        print(f"  - 리츄얼 기록: {ritual_count:,}개")

if __name__ == "__main__":
    check_all_tables()
    
    print("\n" + "="*60)
    print("⚠️  주의사항")
    print("="*60)
    print("1. 수집 데이터(뉴스, 인용문, 정책)는 보존됩니다")
    print("2. 유저 관련 데이터만 삭제됩니다")
    print("3. 삭제 후 복구가 불가능합니다")