"""
DB 리셋 후 뉴스 수집 스크립트
기존 테이블 삭제 후 새로 생성하고 데이터 수집
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db.init_db import reset_db
from scripts.collect_news import collect_all_news


async def main():
    print("=" * 60)
    print("DB 리셋 및 뉴스 수집 시작")
    print("=" * 60)
    
    # 1. DB 완전 초기화
    print("\n1. DB 완전 초기화 중...")
    await reset_db()
    
    # 2. 뉴스 수집
    print("\n2. 뉴스 수집 시작...")
    await collect_all_news()


if __name__ == "__main__":
    asyncio.run(main())