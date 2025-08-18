"""
인용문 수집 실행 스크립트
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.data.quote_extractor import QuoteExtractor
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.tag import Tag


async def main():
    """인용문 수집 메인 함수"""
    
    # QuoteExtractor 초기화
    extractor = QuoteExtractor()
    
    # DB 세션 생성
    async with AsyncSessionLocal() as db:
        # 중분류 태그 조회 (parent_id가 NULL이 아닌 태그)
        stmt = select(Tag).where(Tag.parent_id.isnot(None))
        result = await db.execute(stmt)
        tags = result.scalars().all()
        
        if not tags:
            print("태그가 없습니다. 먼저 태그를 초기화하세요.")
            return
        
        # 태그 정보 준비
        tag_list = [{"id": tag.id, "name": tag.name} for tag in tags]
        
        print(f"수집할 태그: {len(tag_list)}개")
        for tag in tag_list:
            print(f"  - {tag['name']} (ID: {tag['id']})")
        
        # 인용문 수집 시작
        await extractor.collect_all_tag_quotes(
            db=db,
            tags=tag_list,
            quotes_per_tag=100  # 태그당 100개씩
        )


if __name__ == "__main__":
    asyncio.run(main())