"""
인용문 길이 확인 스크립트
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.news import NewsQuote


async def main():
    """인용문 길이 확인"""
    
    async with AsyncSessionLocal() as db:
        stmt = select(NewsQuote)
        result = await db.execute(stmt)
        quotes = result.scalars().all()
        
        print(f"전체 인용문: {len(quotes)}개\n")
        
        # 길이 분석
        max_length = 0
        max_quote = None
        over_2000 = []
        
        for i, q in enumerate(quotes):
            length = len(q.quote_text)
            if length > max_length:
                max_length = length
                max_quote = q
            if length > 2000:
                over_2000.append((i, q, length))
        
        print(f"최대 길이: {max_length}자")
        if max_quote:
            print(f"ID: {max_quote.id}")
            print(f"앞 100자: {max_quote.quote_text[:100]}...")
        
        print(f"\n2000자 초과 인용문: {len(over_2000)}개")
        for idx, q, length in over_2000[:5]:  # 처음 5개만
            print(f"  - 인덱스 {idx}, ID {q.id}: {length}자")


if __name__ == "__main__":
    asyncio.run(main())