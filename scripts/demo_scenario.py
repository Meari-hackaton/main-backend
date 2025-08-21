"""
시연 영상용 데모 시나리오 스크립트
단계별로 데이터를 설정하여 완벽한 시연 환경 구성
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta, date
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.checkin import Ritual, AIPersonaHistory, HeartTree
from app.models.daily import DailyRitual
from app.models.card import MeariSession, GeneratedCard
import json
import uuid

class DemoScenario:
    def __init__(self):
        self.user = None
        self.user_id = None
        
    async def list_users(self):
        """사용자 목록 표시"""
        async with AsyncSessionLocal() as db:
            stmt = select(User).order_by(User.created_at.desc())
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            if not users:
                print("❌ 등록된 사용자가 없습니다.")
                print("💡 먼저 브라우저에서 Google 로그인을 해주세요!")
                return None
            
            print("\n=== 📋 등록된 사용자 목록 ===")
            for i, user in enumerate(users, 1):
                print(f"{i}. {user.nickname or '이름없음'} ({user.email})")
            
            try:
                choice = int(input("\n시연할 사용자 번호를 선택하세요: "))
                if 1 <= choice <= len(users):
                    self.user = users[choice - 1]
                    self.user_id = self.user.id
                    return self.user
            except:
                print("잘못된 입력입니다.")
                return None

    async def scenario_1_fresh_start(self):
        """시나리오 1: 완전 초기화 (첫 방문자)"""
        print("\n🎬 시나리오 1: 첫 방문자 설정")
        print("- 모든 데이터 삭제")
        print("- 태그 선택부터 시작 가능")
        
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            # 모든 데이터 삭제
            await db.execute(text("DELETE FROM generated_cards WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            await db.execute(text("DELETE FROM meari_sessions WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            await db.execute(text("DELETE FROM rituals WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            await db.execute(text("DELETE FROM daily_rituals WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            await db.execute(text("DELETE FROM ai_persona_histories WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            await db.execute(text("DELETE FROM heart_trees WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            await db.execute(text("DELETE FROM user_content_histories WHERE user_id = :user_id"), {"user_id": str(self.user_id)})
            
            await db.commit()
            print("✅ 완전 초기화 완료! 첫 방문자 상태입니다.")

    async def scenario_2_after_onboarding(self):
        """시나리오 2: 온보딩 직후 (공감/성찰 카드 본 상태)"""
        print("\n🎬 시나리오 2: 온보딩 완료 직후")
        print("- 태그 선택 완료")
        print("- 공감/성찰 카드 생성됨")
        print("- 첫 리츄얼 대기 중")
        
        async with AsyncSessionLocal() as db:
            # 기존 데이터 정리
            await self.scenario_1_fresh_start()
            
            # 세션 생성
            session_id = uuid.uuid4()
            session = MeariSession(
                id=session_id,
                user_id=self.user_id,
                selected_tag_ids=[4],  # 취업 문제
                created_at=datetime.utcnow()
            )
            db.add(session)
            
            # 초기 페르소나 생성
            persona_data = {
                "depth": "surface",
                "depth_label": "초기 이해",
                "summary": "취업 준비로 힘든 시기를 보내고 있는 청년",
                "features": ["반복되는 실패로 인한 좌절감", "미래에 대한 불안"],
                "needs": ["실질적인 도움", "정서적 지지"],
                "growth_direction": "자신감 회복과 구체적인 목표 설정"
            }
            
            persona = AIPersonaHistory(
                user_id=self.user_id,
                persona_data=json.dumps(persona_data, ensure_ascii=False),
                event_type="initial",
                is_latest=True,
                event_date=date.today()
            )
            db.add(persona)
            
            # 마음나무 레벨 1
            heart_tree = HeartTree(
                user_id=self.user_id,
                growth_level=1,
                last_grew_at=datetime.now()
            )
            db.add(heart_tree)
            
            await db.commit()
            print("✅ 온보딩 직후 상태 설정 완료!")
            print("   - 태그: 진로/취업")
            print("   - 마음나무 레벨: 1")

    async def scenario_3_ritual_ready(self):
        """시나리오 3: 리츄얼 받기 가능 상태"""
        print("\n🎬 시나리오 3: 리츄얼 받기 버튼 활성화")
        print("- 오늘의 리츄얼 없음")
        print("- '리츄얼 받기' 버튼 클릭 가능")
        
        async with AsyncSessionLocal() as db:
            # 오늘의 리츄얼만 삭제
            from sqlalchemy import text
            today = date.today()
            await db.execute(
                text("DELETE FROM daily_rituals WHERE user_id = :user_id AND date = :today"),
                {"user_id": str(self.user_id), "today": today}
            )
            await db.commit()
            print("✅ 오늘의 리츄얼 삭제 완료! 리츄얼 받기 가능합니다.")

    async def scenario_4_mid_journey(self):
        """시나리오 4: 14일차 중간 지점"""
        print("\n🎬 시나리오 4: 14일차 여정 중")
        print("- 마음나무 레벨 14 (성장 단계)")
        print("- 페르소나 3단계 진화")
        print("- 오늘 리츄얼 미완료")
        
        async with AsyncSessionLocal() as db:
            await self.scenario_1_fresh_start()
            
            base_date = date.today() - timedelta(days=14)
            
            # 14일치 리츄얼 생성
            for i in range(14):
                ritual_date = base_date + timedelta(days=i)
                
                # DailyRitual 생성
                daily_ritual = DailyRitual(
                    user_id=self.user_id,
                    date=ritual_date,
                    ritual_title=f"Day {i+1} 리츄얼",
                    ritual_description="10분 명상과 감사일기",
                    ritual_type="meditation" if i % 2 == 0 else "writing",
                    duration_minutes=10,
                    is_completed=(i < 13),  # 오늘(14일차)만 미완료
                    completed_at=datetime.combine(ritual_date, datetime.min.time()) if i < 13 else None
                )
                db.add(daily_ritual)
            
            # 페르소나 진화 (3단계)
            persona_data = {
                "depth": "moderate",
                "depth_label": "중간 이해",
                "summary": "14일간의 꾸준한 실천으로 변화를 경험 중",
                "features": ["작은 성취감 축적", "루틴 형성 중"],
                "needs": ["지속적인 동기부여", "구체적인 피드백"],
                "growth_direction": "더 깊은 자기 이해를 향해"
            }
            
            persona = AIPersonaHistory(
                user_id=self.user_id,
                persona_data=json.dumps(persona_data, ensure_ascii=False),
                event_type="ritual_update",
                is_latest=True,
                event_date=date.today()
            )
            db.add(persona)
            
            # 마음나무 레벨 14
            heart_tree = HeartTree(
                user_id=self.user_id,
                growth_level=14,
                last_grew_at=datetime.now()
            )
            db.add(heart_tree)
            
            await db.commit()
            print("✅ 14일차 상태 설정 완료!")
            print("   - 마음나무: 성장 단계 (14/28)")
            print("   - 오늘 리츄얼: 미완료 상태")

    async def scenario_5_completion_ready(self):
        """시나리오 5: 28일 완주 (리포트 보기 가능)"""
        print("\n🎬 시나리오 5: 28일 완주 상태")
        print("- 마음나무 만개 (레벨 28)")
        print("- 28일 완주 리포트 버튼 활성화")
        print("- 모든 리츄얼 완료")
        
        async with AsyncSessionLocal() as db:
            await self.scenario_1_fresh_start()
            
            base_date = date.today() - timedelta(days=30)
            
            # 28일치 데이터 생성
            for i in range(28):
                ritual_date = base_date + timedelta(days=i)
                
                # 3일마다 Ritual 생성
                if i % 3 == 0:
                    ritual = Ritual(
                        user_id=self.user_id,
                        ritual_sequence=i + 1,
                        diary_entry=f"Day {i+1}: 오늘도 한 걸음 더 성장했습니다.",
                        selected_mood="평온" if i > 14 else "불안",
                        ritual_completed=True,
                        checkin_date=ritual_date
                    )
                    db.add(ritual)
                
                # 매일 DailyRitual
                daily_ritual = DailyRitual(
                    user_id=self.user_id,
                    date=ritual_date,
                    ritual_title=f"Day {i+1} 리츄얼",
                    ritual_description="명상과 감사일기",
                    ritual_type="meditation" if i % 2 == 0 else "writing",
                    duration_minutes=10,
                    is_completed=True,
                    completed_at=datetime.combine(ritual_date, datetime.min.time()) + timedelta(hours=20)
                )
                db.add(daily_ritual)
            
            # 5단계 페르소나 진화
            stages = [
                {"day": 1, "depth": "surface", "label": "초기 이해"},
                {"day": 7, "depth": "shallow", "label": "얕은 탐색"},
                {"day": 14, "depth": "moderate", "label": "중간 이해"},
                {"day": 21, "depth": "deep", "label": "깊은 통찰"},
                {"day": 28, "depth": "wisdom", "label": "지혜로운 성장"}
            ]
            
            for stage in stages:
                persona_data = {
                    "depth": stage["depth"],
                    "depth_label": stage["label"],
                    "summary": f"{stage['day']}일차: {stage['label']} 단계",
                    "features": [f"Day {stage['day']} 특징"],
                    "needs": ["지속적인 성장"],
                    "growth_direction": "완성을 향해"
                }
                
                persona = AIPersonaHistory(
                    user_id=self.user_id,
                    persona_data=json.dumps(persona_data, ensure_ascii=False),
                    event_type="ritual_update" if stage["day"] > 1 else "initial",
                    is_latest=(stage["day"] == 28),
                    event_date=base_date + timedelta(days=stage["day"]-1)
                )
                db.add(persona)
            
            # 마음나무 만개
            heart_tree = HeartTree(
                user_id=self.user_id,
                growth_level=28,
                last_grew_at=datetime.now()
            )
            db.add(heart_tree)
            
            await db.commit()
            print("✅ 28일 완주 상태 설정 완료!")
            print("   - 마음나무: 만개 🌸")
            print("   - 리포트 보기 가능")

    async def scenario_6_custom_day(self):
        """시나리오 6: 특정 일차 설정"""
        print("\n🎬 시나리오 6: 원하는 일차 설정")
        
        try:
            days = int(input("설정할 일차 (1-28): "))
            if not 1 <= days <= 28:
                print("1-28 사이의 숫자를 입력해주세요.")
                return
        except:
            print("잘못된 입력입니다.")
            return
        
        async with AsyncSessionLocal() as db:
            await self.scenario_1_fresh_start()
            
            base_date = date.today() - timedelta(days=days+2)
            
            # 입력한 일수만큼 리츄얼 생성
            for i in range(days):
                ritual_date = base_date + timedelta(days=i)
                
                daily_ritual = DailyRitual(
                    user_id=self.user_id,
                    date=ritual_date,
                    ritual_title=f"Day {i+1} 리츄얼",
                    ritual_description="맞춤형 리츄얼",
                    ritual_type="meditation",
                    duration_minutes=10,
                    is_completed=True,
                    completed_at=datetime.combine(ritual_date, datetime.min.time())
                )
                db.add(daily_ritual)
            
            # 마음나무 레벨 설정
            heart_tree = HeartTree(
                user_id=self.user_id,
                growth_level=days,
                last_grew_at=datetime.now()
            )
            db.add(heart_tree)
            
            await db.commit()
            
            stage = "씨앗" if days <= 6 else "새싹" if days <= 13 else "성장" if days <= 20 else "개화" if days <= 27 else "만개"
            print(f"✅ {days}일차 상태 설정 완료!")
            print(f"   - 마음나무: {stage} 단계 ({days}/28)")

async def main():
    demo = DemoScenario()
    
    # 사용자 선택
    user = await demo.list_users()
    if not user:
        return
    
    print(f"\n선택된 사용자: {user.nickname} ({user.email})")
    
    while True:
        print("\n" + "="*50)
        print("🎬 시연 시나리오 선택")
        print("="*50)
        print("1. 🆕 첫 방문자 (완전 초기화)")
        print("2. 📝 온보딩 직후 (태그 선택 완료)")
        print("3. 🎯 리츄얼 받기 가능 (오늘 리츄얼 없음)")
        print("4. 🌱 14일차 중간 지점")
        print("5. 🌸 28일 완주 (리포트 보기)")
        print("6. 🎨 커스텀 일차 설정")
        print("0. 종료")
        print("="*50)
        
        choice = input("\n선택 (0-6): ")
        
        if choice == "0":
            print("👋 종료합니다.")
            break
        elif choice == "1":
            await demo.scenario_1_fresh_start()
        elif choice == "2":
            await demo.scenario_2_after_onboarding()
        elif choice == "3":
            await demo.scenario_3_ritual_ready()
        elif choice == "4":
            await demo.scenario_4_mid_journey()
        elif choice == "5":
            await demo.scenario_5_completion_ready()
        elif choice == "6":
            await demo.scenario_6_custom_day()
        else:
            print("잘못된 선택입니다.")
        
        print("\n✨ 이제 브라우저에서 확인해보세요!")
        print("   http://localhost:3000")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║   🎬 메아리 시연 영상 데모 설정기    ║
    ╚══════════════════════════════════════╝
    """)
    asyncio.run(main())