"""
유저 관련 데이터만 삭제하는 스크립트
수집한 뉴스, 인용문, 태그 데이터는 보존됨
"""
import asyncio
from sqlalchemy import create_engine, text
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

def clear_user_data():
    """유저 관련 데이터만 삭제"""
    
    print("\n" + "="*60)
    print("🗑️  유저 데이터 삭제 스크립트")
    print("="*60)
    
    # 삭제할 테이블 목록 (외래키 의존성 순서대로)
    tables_to_clear = [
        "user_content_histories",  # 콘텐츠 이력
        "generated_cards",          # 생성된 카드
        "ai_persona_histories",     # AI 페르소나
        "rituals",                  # 리츄얼
        "heart_trees",              # 마음나무
        "daily_rituals",            # 일일 리츄얼
        "user_streaks",             # 연속 기록
        "meari_sessions",           # 메아리 세션
        "user_sessions",            # 사용자 세션
        "users"                     # 사용자
    ]
    
    with SessionLocal() as session:
        try:
            # 삭제 전 데이터 개수 확인
            print("\n📊 삭제 전 데이터 현황:")
            print("-" * 40)
            total_before = 0
            for table in tables_to_clear:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table:30} : {count:,} 행")
                total_before += count
            print(f"  {'총계':30} : {total_before:,} 행")
            
            # 사용자 확인
            print("\n" + "="*60)
            confirmation = input("⚠️  정말로 모든 유저 데이터를 삭제하시겠습니까? (yes/no): ")
            
            if confirmation.lower() != 'yes':
                print("❌ 삭제 취소됨")
                return
            
            # 데이터 삭제
            print("\n🔄 데이터 삭제 중...")
            print("-" * 40)
            
            for table in tables_to_clear:
                result = session.execute(text(f"DELETE FROM {table}"))
                deleted_count = result.rowcount
                print(f"  {table:30} : {deleted_count:,} 행 삭제됨")
            
            # 커밋
            session.commit()
            print("\n✅ 모든 유저 데이터가 삭제되었습니다.")
            
            # 삭제 후 확인
            print("\n📊 삭제 후 데이터 현황:")
            print("-" * 40)
            
            # 유저 테이블 확인
            for table in tables_to_clear:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table:30} : {count:,} 행")
            
            # 수집 데이터 확인
            print("\n💾 보존된 수집 데이터:")
            print("-" * 40)
            preserved_tables = ["news", "news_quotes", "tags", "youth_policies"]
            for table in preserved_tables:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table:30} : {count:,} 행")
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ 오류 발생: {e}")
            raise
        
    print("\n" + "="*60)
    print("✅ 유저 데이터 삭제 완료!")
    print("💾 수집 데이터는 안전하게 보존되었습니다.")
    print("="*60)

if __name__ == "__main__":
    clear_user_data()