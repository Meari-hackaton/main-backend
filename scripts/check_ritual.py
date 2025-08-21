"""
오늘의 리츄얼 확인 및 삭제 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import date
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.daily import DailyRitual

async def check_and_delete_today_ritual():
    """오늘의 리츄얼 확인 및 삭제"""
    async with AsyncSessionLocal() as db:
        # 사용자 목록
        stmt = select(User).order_by(User.created_at.desc())
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            print("등록된 사용자가 없습니다.")
            return
        
        print("\n=== 사용자별 오늘의 리츄얼 확인 ===")
        today = date.today()
        
        for user in users:
            # 오늘의 리츄얼 확인
            stmt = select(DailyRitual).where(
                DailyRitual.user_id == user.id,
                DailyRitual.date == today
            )
            result = await db.execute(stmt)
            ritual = result.scalar_one_or_none()
            
            if ritual:
                print(f"\n✅ {user.nickname} ({user.email})")
                print(f"   - 리츄얼: {ritual.ritual_title}")
                print(f"   - 타입: {ritual.ritual_type}")
                print(f"   - 완료: {ritual.is_completed}")
                
                # 삭제 여부 확인
                delete = input("   이 리츄얼을 삭제하시겠습니까? (y/n): ")
                if delete.lower() == 'y':
                    await db.delete(ritual)
                    await db.commit()
                    print("   ✅ 삭제 완료!")
                else:
                    print("   ⏭️ 건너뜀")
            else:
                print(f"\n⚪ {user.nickname} ({user.email})")
                print("   - 오늘의 리츄얼 없음")

async def delete_all_today_rituals():
    """모든 사용자의 오늘 리츄얼 삭제"""
    async with AsyncSessionLocal() as db:
        today = date.today()
        
        # 오늘의 모든 리츄얼 삭제
        await db.execute(
            text("DELETE FROM daily_rituals WHERE date = :today"),
            {"today": today}
        )
        await db.commit()
        print(f"\n✅ {today} 모든 리츄얼 삭제 완료!")

async def main():
    print("""
    ====================================
    오늘의 리츄얼 관리
    ====================================
    1. 사용자별 확인 및 개별 삭제
    2. 모든 사용자 오늘 리츄얼 일괄 삭제
    ====================================
    """)
    
    choice = input("선택 (1-2): ")
    
    if choice == "1":
        await check_and_delete_today_ritual()
    elif choice == "2":
        confirm = input("정말 모든 사용자의 오늘 리츄얼을 삭제하시겠습니까? (yes/no): ")
        if confirm.lower() == "yes":
            await delete_all_today_rituals()
        else:
            print("취소되었습니다.")
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    asyncio.run(main())