"""
오늘의 리츄얼 삭제 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import date
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def delete_today_rituals():
    """오늘의 모든 리츄얼 삭제"""
    async with AsyncSessionLocal() as db:
        today = date.today()
        
        # 오늘의 모든 리츄얼 삭제
        result = await db.execute(
            text("DELETE FROM daily_rituals WHERE date = :today"),
            {"today": today}
        )
        await db.commit()
        
        print(f"✅ {today} 날짜의 모든 리츄얼 삭제 완료!")
        print(f"   삭제된 리츄얼 수: {result.rowcount}개")
        print("\n이제 브라우저에서:")
        print("1. 대시보드 새로고침 (F5)")
        print("2. '리츄얼 받기' 버튼이 활성화됩니다")

if __name__ == "__main__":
    asyncio.run(delete_today_rituals())