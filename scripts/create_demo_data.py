"""
28일 완주 시연용 Mock 데이터 생성 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta, date
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.checkin import Ritual, AIPersonaHistory, HeartTree
from app.models.daily import DailyRitual
import json
import uuid

async def list_users():
    """모든 사용자 목록 표시"""
    async with AsyncSessionLocal() as db:
        stmt = select(User).order_by(User.created_at.desc())
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            print("등록된 사용자가 없습니다.")
            return None
        
        print("\n=== 등록된 사용자 목록 ===")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.nickname or '이름없음'} ({user.email})")
        
        try:
            choice = int(input("\n데모 데이터를 생성할 사용자 번호를 선택하세요: "))
            if 1 <= choice <= len(users):
                return users[choice - 1]
            else:
                print("잘못된 번호입니다.")
                return None
        except ValueError:
            print("숫자를 입력해주세요.")
            return None

async def create_demo_data(user):
    """특정 사용자에게 28일치 데이터 생성"""
    
    async with AsyncSessionLocal() as db:
        user_id = user.id
        print(f"\n{user.nickname} ({user.email})님의 데모 데이터 생성 시작...")
        
        # 기존 데이터 삭제
        print("기존 데이터 정리 중...")
        
        # 기존 리츄얼 삭제
        from sqlalchemy import text
        await db.execute(
            text("DELETE FROM rituals WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        
        # 기존 DailyRitual 삭제
        await db.execute(
            text("DELETE FROM daily_rituals WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        
        # 1. 28일치 리츄얼 생성
        base_date = date.today() - timedelta(days=30)
        
        print("28일치 리츄얼 생성 중...")
        for i in range(28):
            ritual_date = base_date + timedelta(days=i)
            
            # Ritual 생성 (메아리 세션 리츄얼) - 3일마다
            if i % 3 == 0:
                ritual = Ritual(
                    user_id=user_id,
                    ritual_sequence=i + 1,
                    diary_entry=f"Day {i+1}: 오늘은 조금 더 나아진 느낌이에요.",
                    selected_mood="평온" if i > 14 else "불안",
                    ritual_completed=True,
                    checkin_date=ritual_date,
                    created_at=datetime.combine(ritual_date, datetime.min.time())
                )
                db.add(ritual)
            
            # DailyRitual 생성
            daily_ritual = DailyRitual(
                user_id=user_id,
                date=ritual_date,
                ritual_title=f"Day {i+1} 리츄얼",
                ritual_description="10분 명상과 감사일기 쓰기",
                ritual_type="meditation" if i % 2 == 0 else "writing",
                duration_minutes=10,
                is_completed=True,
                completed_at=datetime.combine(ritual_date, datetime.min.time()) + timedelta(hours=20),
                difficulty_rating=3,
                user_mood="calm" if i > 20 else "anxious",
                user_note=f"Day {i+1} 완료!"
            )
            db.add(daily_ritual)
        
        # 2. 페르소나 진화 히스토리 생성
        print("페르소나 진화 히스토리 생성 중...")
        persona_stages = [
            {"depth": "surface", "depth_label": "초기 이해", "day": 1},
            {"depth": "shallow", "depth_label": "얕은 탐색", "day": 7},
            {"depth": "moderate", "depth_label": "중간 이해", "day": 14},
            {"depth": "deep", "depth_label": "깊은 통찰", "day": 21},
            {"depth": "wisdom", "depth_label": "지혜로운 성장", "day": 28}
        ]
        
        for stage in persona_stages:
            persona_data = {
                "depth": stage["depth"],
                "depth_label": stage["depth_label"],
                "summary": f"{stage['day']}일차: {stage['depth_label']} 단계 도달",
                "features": [
                    f"특징 1: {stage['depth_label']} 수준의 자기 이해",
                    f"특징 2: 점진적 성장 중"
                ],
                "needs": ["지속적인 실천", "꾸준한 성찰"],
                "growth_direction": "더 깊은 자기 이해를 향해"
            }
            
            history = AIPersonaHistory(
                user_id=user_id,
                persona_data=json.dumps(persona_data, ensure_ascii=False),
                event_type="ritual_update" if stage["day"] > 1 else "initial",
                event_date=base_date + timedelta(days=stage["day"]-1),
                is_latest=(stage["day"] == 28)
            )
            db.add(history)
        
        # 3. 마음나무 레벨 28 설정
        print("마음나무 레벨 설정 중...")
        stmt = select(HeartTree).where(HeartTree.user_id == user_id)
        result = await db.execute(stmt)
        heart_tree = result.scalar_one_or_none()
        
        if heart_tree:
            heart_tree.growth_level = 28
            heart_tree.last_grew_at = datetime.now()
        else:
            heart_tree = HeartTree(
                user_id=user_id,
                growth_level=28,
                last_grew_at=datetime.now()
            )
            db.add(heart_tree)
        
        await db.commit()
        print("\n✅ 28일 완주 데모 데이터 생성 완료!")
        print("- 28개 리츄얼 생성")
        print("- 5단계 페르소나 진화")
        print("- 마음나무 레벨 28 설정")
        print("\n이제 브라우저에서:")
        print("1. 대시보드 새로고침 (F5)")
        print("2. '🎉 28일 완주 리포트 보기' 버튼 클릭")
        print("3. 또는 직접 이동: http://localhost:3000/completion")

async def reset_demo_data(user):
    """데모 데이터 초기화"""
    
    async with AsyncSessionLocal() as db:
        user_id = user.id
        print(f"\n{user.nickname} ({user.email})님의 데이터 초기화 중...")
        
        from sqlalchemy import text
        
        # 리츄얼 삭제
        await db.execute(
            text("DELETE FROM rituals WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        
        # DailyRitual 삭제
        await db.execute(
            text("DELETE FROM daily_rituals WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        
        # 페르소나 히스토리 삭제
        await db.execute(
            text("DELETE FROM ai_persona_histories WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        
        # 마음나무 리셋
        await db.execute(
            text("UPDATE heart_trees SET growth_level = 0 WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        
        await db.commit()
        print("✅ 데모 데이터 초기화 완료!")

async def main():
    # 사용자 목록 표시 및 선택
    user = await list_users()
    if not user:
        return
    
    print("\n=== 작업 선택 ===")
    print("1. 28일 완주 데이터 생성")
    print("2. 데이터 초기화")
    print("3. 취소")
    
    choice = input("\n선택: ")
    
    if choice == "1":
        await create_demo_data(user)
    elif choice == "2":
        await reset_demo_data(user)
    else:
        print("취소되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())