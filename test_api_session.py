import requests
import json

# FastAPI 서버가 실행 중이어야 함
BASE_URL = "http://localhost:8001/api/v1"

def test_create_session():
    """메아리 세션 생성 API 테스트"""
    
    # 요청 데이터
    request_data = {
        "selected_tag_id": 2,  # 직장 내 번아웃
        "user_context": "매일 야근하고 주말에도 일해야 해서 너무 지쳐있어요. 회사를 그만두고 싶은데 다음 직장을 구할 수 있을지 불안합니다.",
        "user_id": None
    }
    
    print("=" * 50)
    print("메아리 세션 생성 API 테스트")
    print("=" * 50)
    print(f"\n요청 데이터:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    try:
        # API 호출
        response = requests.post(
            f"{BASE_URL}/meari/sessions",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n응답 상태 코드: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            
            print("\n✅ 세션 생성 성공!")
            print(f"- Session ID: {result.get('session_id')}")
            print(f"- Timestamp: {result.get('timestamp')}")
            
            # 카드 확인
            cards = result.get('cards', {})
            print(f"\n생성된 카드:")
            for card_type, card_data in cards.items():
                print(f"  - {card_type}: {card_data.get('type', 'N/A')}")
                if 'content' in card_data:
                    print(f"    Content: {card_data['content'][:50]}...")
            
            # 페르소나 확인
            persona = result.get('persona', {})
            if persona:
                print(f"\n페르소나:")
                print(f"  - Depth: {persona.get('depth')}")
                print(f"  - Label: {persona.get('depth_label')}")
                print(f"  - Summary: {persona.get('summary', '')[:50]}...")
            
            # 성장 콘텐츠 확인
            growth = result.get('growth_content', {})
            if growth:
                print(f"\n성장 콘텐츠:")
                for content_type in growth.keys():
                    print(f"  - {content_type}")
                    
        else:
            print(f"\n❌ 오류 발생:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 서버 연결 실패. FastAPI 서버가 실행 중인지 확인하세요.")
        print("실행 명령: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")


if __name__ == "__main__":
    test_create_session()