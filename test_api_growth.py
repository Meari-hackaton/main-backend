import requests
import json
import uuid

# FastAPI 서버가 실행 중이어야 함
BASE_URL = "http://localhost:8001/api/v1"

def test_growth_contents():
    """성장 콘텐츠 생성 API 테스트"""
    
    # 먼저 세션 생성
    session_request = {
        "selected_tag_id": 2,
        "user_context": "번아웃으로 지친 상태입니다",
        "user_id": None
    }
    
    print("=" * 50)
    print("1. 먼저 메아리 세션 생성")
    print("=" * 50)
    
    session_response = requests.post(
        f"{BASE_URL}/meari/sessions",
        json=session_request
    )
    
    if session_response.status_code != 201:
        print(f"❌ 세션 생성 실패: {session_response.text}")
        return
    
    session_data = session_response.json()
    session_id = session_data.get("session_id")
    print(f"✅ 세션 생성 성공: {session_id}")
    
    # 성장 콘텐츠 요청
    growth_request = {
        "context": "initial",
        "session_id": session_id,
        "persona_summary": "번아웃으로 지친 청년 직장인",
        "previous_policy_ids": [],
        "user_id": None
    }
    
    print("\n" + "=" * 50)
    print("2. 성장 콘텐츠 생성 요청")
    print("=" * 50)
    print(f"요청 데이터:")
    print(json.dumps(growth_request, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/meari/growth-contents",
            json=growth_request,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n응답 상태 코드: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("\n✅ 성장 콘텐츠 생성 성공!")
            
            # 카드 확인
            cards = result.get('cards', {})
            print(f"\n생성된 카드:")
            for card_type, card_data in cards.items():
                print(f"\n  [{card_type}]")
                if isinstance(card_data, dict):
                    print(f"    - Title: {card_data.get('title', 'N/A')}")
                    if card_type == "information":
                        print(f"    - Search Query: {card_data.get('search_query', 'N/A')}")
                        print(f"    - Summary: {card_data.get('summary', 'N/A')[:100]}...")
                    elif card_type == "experience":
                        print(f"    - Activity: {card_data.get('activity', 'N/A')[:100]}...")
                        print(f"    - Duration: {card_data.get('duration', 'N/A')}")
                    elif card_type == "support":
                        print(f"    - Policy: {card_data.get('policy_name', 'N/A')}")
                        print(f"    - Organization: {card_data.get('organization', 'N/A')}")
        else:
            print(f"\n❌ 오류 발생:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 서버 연결 실패. FastAPI 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")


def test_ritual():
    """리츄얼 기록 API 테스트"""
    
    print("\n" + "=" * 50)
    print("3. 리츄얼 기록 테스트")
    print("=" * 50)
    
    ritual_request = {
        "diary_entry": "오늘은 추천받은 명상을 시도해봤어요. 생각보다 마음이 편안해졌습니다.",
        "selected_mood": "hopeful",
        "growth_contents_viewed": ["card_001", "card_002"],
        "user_id": None
    }
    
    print(f"요청 데이터:")
    print(json.dumps(ritual_request, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/meari/rituals",
            json=ritual_request,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n응답 상태 코드: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("\n✅ 리츄얼 기록 성공!")
            
            # 마음나무 상태
            tree = result.get('tree', {})
            print(f"\n마음나무 상태:")
            print(f"  - Stage: {tree.get('stage_label')} ({tree.get('stage')})")
            print(f"  - Progress: {tree.get('progress')}/28")
            print(f"  - Percentage: {tree.get('percentage'):.1f}%")
            
            # 페르소나 업데이트 확인
            persona = result.get('persona', {})
            if persona.get('updated'):
                print(f"\n페르소나 업데이트됨!")
                print(f"  - Depth: {persona.get('depth')}")
                print(f"  - Summary: {persona.get('summary', '')[:100]}...")
            
            # 메시지
            message = result.get('message')
            print(f"\n메시지: {message}")
            
        else:
            print(f"\n❌ 오류 발생:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 서버 연결 실패. FastAPI 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")


if __name__ == "__main__":
    print("메아리 API 통합 테스트")
    print("=" * 80)
    
    # 1. 성장 콘텐츠 테스트
    test_growth_contents()
    
    # 2. 리츄얼 테스트
    test_ritual()