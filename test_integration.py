#!/usr/bin/env python
"""
메아리 백엔드 통합 테스트
전체 플로우를 검증합니다.
"""
import requests
import json
import time
import uuid
from typing import Dict, Any

BASE_URL = "http://localhost:8001/api/v1"

class MeariIntegrationTest:
    def __init__(self):
        self.session_id = None
        self.user_id = None
        self.policy_ids = []
        self.timings = {}
    
    def test_full_flow(self):
        """전체 플로우 테스트"""
        print("=" * 80)
        print("메아리 백엔드 통합 테스트")
        print("=" * 80)
        
        # 1. 세션 생성
        self.test_create_session()
        
        # 2. 첫 번째 성장 콘텐츠
        self.test_growth_content_initial()
        
        # 3. 리츄얼 기록
        self.test_ritual(1)
        
        # 4. 두 번째 성장 콘텐츠 (중복 방지 확인)
        self.test_growth_content_ritual()
        
        # 5. 여러 리츄얼 기록 (마음나무 성장)
        for i in range(2, 8):
            self.test_ritual(i)
        
        # 6. 성능 리포트
        self.print_performance_report()
    
    def test_create_session(self):
        """세션 생성 테스트"""
        print("\n[1] 메아리 세션 생성")
        print("-" * 40)
        
        request_data = {
            "selected_tag_id": 2,
            "user_context": "매일 야근하고 번아웃 상태입니다. 회사를 그만두고 싶어요."
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/meari/sessions",
            json=request_data
        )
        elapsed = time.time() - start_time
        self.timings['session_creation'] = elapsed
        
        if response.status_code == 201:
            result = response.json()
            self.session_id = result.get("session_id")
            print(f"✅ 세션 생성 성공 (소요시간: {elapsed:.2f}초)")
            print(f"   Session ID: {self.session_id}")
            
            # 카드 확인
            cards = result.get("cards", {})
            if "empathy" in cards:
                print(f"   - 공감 카드: ✓")
            if "reflection" in cards:
                print(f"   - 성찰 카드: ✓")
            
            # 페르소나 확인
            persona = result.get("persona", {})
            if persona:
                print(f"   - 초기 페르소나: {persona.get('depth', 'N/A')}")
        else:
            print(f"❌ 세션 생성 실패: {response.status_code}")
            print(response.text)
    
    def test_growth_content_initial(self):
        """초기 성장 콘텐츠 테스트"""
        print("\n[2] 초기 성장 콘텐츠 생성")
        print("-" * 40)
        
        if not self.session_id:
            print("❌ 세션 ID가 없습니다")
            return
        
        request_data = {
            "context": "initial",
            "session_id": self.session_id,
            "previous_policy_ids": []
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/meari/growth-contents",
            json=request_data
        )
        elapsed = time.time() - start_time
        self.timings['growth_initial'] = elapsed
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ 성장 콘텐츠 생성 성공 (소요시간: {elapsed:.2f}초)")
            
            cards = result.get("cards", {})
            if "information" in cards:
                print(f"   - 정보 카드: {cards['information'].get('title', 'N/A')}")
            if "experience" in cards:
                print(f"   - 경험 카드: {cards['experience'].get('title', 'N/A')}")
            if "support" in cards:
                support = cards['support']
                policy_name = support.get('policy_name', 'N/A')
                print(f"   - 지원 카드: {policy_name}")
                # 정책 ID 저장 (중복 테스트용)
                if support.get('policy_id'):
                    self.policy_ids.append(support['policy_id'])
        else:
            print(f"❌ 성장 콘텐츠 생성 실패: {response.status_code}")
            print(response.text)
    
    def test_ritual(self, sequence: int):
        """리츄얼 기록 테스트"""
        print(f"\n[{sequence+2}] 리츄얼 기록 #{sequence}")
        print("-" * 40)
        
        moods = ["hopeful", "calm", "tired", "anxious", "peaceful"]
        diary_entries = [
            "오늘은 추천받은 명상을 해봤어요. 조금 나아진 것 같아요.",
            "일찍 잠들기 리츄얼을 실천했습니다. 개운해요.",
            "동료와 대화를 나눴어요. 혼자가 아니란 걸 느꼈습니다.",
            "산책을 하면서 생각을 정리했어요.",
            "일기를 쓰면서 하루를 돌아봤습니다.",
            "요가를 하면서 몸과 마음을 이완시켰어요.",
            "좋아하는 음악을 들으며 휴식을 취했습니다."
        ]
        
        request_data = {
            "diary_entry": diary_entries[sequence % len(diary_entries)],
            "selected_mood": moods[sequence % len(moods)],
            "growth_contents_viewed": []
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/meari/rituals",
            json=request_data
        )
        elapsed = time.time() - start_time
        self.timings[f'ritual_{sequence}'] = elapsed
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ 리츄얼 기록 성공 (소요시간: {elapsed:.2f}초)")
            
            # 마음나무 상태
            tree = result.get("tree", {})
            print(f"   - 마음나무: {tree.get('stage_label')} ({tree.get('progress')}/28)")
            print(f"   - 진행률: {tree.get('percentage', 0):.1f}%")
            
            # 페르소나 업데이트
            persona = result.get("persona", {})
            if persona.get("updated"):
                print(f"   - 페르소나 업데이트: {persona.get('depth')}")
            
            # 메시지
            message = result.get("message", "")
            if message:
                print(f"   - 메시지: {message}")
        else:
            print(f"❌ 리츄얼 기록 실패: {response.status_code}")
            print(response.text)
    
    def test_growth_content_ritual(self):
        """리츄얼 후 성장 콘텐츠 (중복 방지 테스트)"""
        print("\n[4] 리츄얼 후 성장 콘텐츠 (중복 방지 테스트)")
        print("-" * 40)
        
        if not self.session_id:
            print("❌ 세션 ID가 없습니다")
            return
        
        request_data = {
            "context": "ritual",
            "session_id": self.session_id,
            "previous_policy_ids": self.policy_ids  # 이전에 본 정책 ID
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/meari/growth-contents",
            json=request_data
        )
        elapsed = time.time() - start_time
        self.timings['growth_ritual'] = elapsed
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ 성장 콘텐츠 생성 성공 (소요시간: {elapsed:.2f}초)")
            
            cards = result.get("cards", {})
            if "support" in cards:
                support = cards['support']
                policy_name = support.get('policy_name', 'N/A')
                policy_id = support.get('policy_id')
                
                # 중복 확인
                if policy_id in self.policy_ids:
                    print(f"   ⚠️ 중복된 정책이 추천됨: {policy_name}")
                else:
                    print(f"   ✓ 새로운 정책 추천: {policy_name}")
                    if policy_id:
                        self.policy_ids.append(policy_id)
        else:
            print(f"❌ 성장 콘텐츠 생성 실패: {response.status_code}")
            print(response.text)
    
    def print_performance_report(self):
        """성능 리포트 출력"""
        print("\n" + "=" * 80)
        print("성능 측정 결과")
        print("=" * 80)
        
        for key, value in self.timings.items():
            print(f"{key:20s}: {value:6.2f}초")
        
        # 평균 계산
        ritual_times = [v for k, v in self.timings.items() if k.startswith('ritual_')]
        if ritual_times:
            avg_ritual = sum(ritual_times) / len(ritual_times)
            print(f"\n{'평균 리츄얼 시간':20s}: {avg_ritual:6.2f}초")
        
        # 목표 대비 평가
        print("\n목표 대비 평가:")
        if 'session_creation' in self.timings:
            if self.timings['session_creation'] <= 10:
                print(f"  ✅ 세션 생성: {self.timings['session_creation']:.2f}초 (목표: 8-10초)")
            else:
                print(f"  ⚠️ 세션 생성: {self.timings['session_creation']:.2f}초 (목표: 8-10초 초과)")
        
        if ritual_times:
            if avg_ritual <= 0.5:
                print(f"  ✅ 리츄얼 기록: {avg_ritual:.2f}초 (목표: 0.5초)")
            else:
                print(f"  ⚠️ 리츄얼 기록: {avg_ritual:.2f}초 (목표: 0.5초 초과)")


if __name__ == "__main__":
    test = MeariIntegrationTest()
    test.test_full_flow()