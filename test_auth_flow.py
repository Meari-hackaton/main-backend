"""
Google OAuth 인증 플로우 통합 테스트
"""
import asyncio
import httpx
from datetime import datetime

API_URL = "http://localhost:8000"


async def test_auth_flow():
    """인증 플로우 테스트"""
    
    async with httpx.AsyncClient() as client:
        print("\n=== Google OAuth 인증 플로우 테스트 ===\n")
        
        # 1. 로그인하지 않은 상태에서 /auth/me 접근
        print("1. 로그인하지 않은 상태에서 사용자 정보 요청...")
        try:
            response = await client.get(f"{API_URL}/auth/me")
            print(f"   상태 코드: {response.status_code}")
            print(f"   응답: {response.json()}")
            assert response.status_code == 401, "인증되지 않은 상태에서 401이 반환되어야 합니다"
            print("   ✅ 인증 필요 확인 완료\n")
        except Exception as e:
            print(f"   ❌ 에러: {e}\n")
        
        # 2. 로그인하지 않은 상태에서 메아리 API 접근
        print("2. 로그인하지 않은 상태에서 메아리 세션 생성 요청...")
        try:
            response = await client.post(
                f"{API_URL}/api/v1/meari/sessions",
                json={
                    "selected_tag_id": 2,
                    "user_context": "테스트 고민입니다"
                }
            )
            print(f"   상태 코드: {response.status_code}")
            print(f"   응답: {response.json()}")
            assert response.status_code == 401, "인증되지 않은 상태에서 401이 반환되어야 합니다"
            print("   ✅ 메아리 API 보호 확인 완료\n")
        except Exception as e:
            print(f"   ❌ 에러: {e}\n")
        
        # 3. Google OAuth 로그인 URL 확인
        print("3. Google OAuth 로그인 URL 확인...")
        print(f"   로그인 URL: {API_URL}/auth/google/login")
        print("   브라우저에서 이 URL로 접속하면 Google 로그인 페이지로 리다이렉트됩니다.\n")
        
        # 4. 로그인 후 테스트 안내
        print("=== 수동 테스트 필요 ===")
        print("1. 브라우저에서 Google 로그인 진행")
        print("2. 로그인 성공 시 http://localhost:3000/dashboard?login=success로 리다이렉트")
        print("3. 브라우저 개발자 도구에서 'meari_session' 쿠키 확인")
        print("4. 쿠키 값을 복사하여 아래 테스트에 사용\n")
        
        # 세션 쿠키 입력 받기 (수동 테스트용)
        session_cookie = input("세션 쿠키 값을 입력하세요 (테스트 건너뛰려면 Enter): ").strip()
        
        if session_cookie:
            # 5. 인증된 상태에서 사용자 정보 조회
            print("\n5. 인증된 상태에서 사용자 정보 조회...")
            cookies = {"meari_session": session_cookie}
            
            try:
                response = await client.get(f"{API_URL}/auth/me", cookies=cookies)
                print(f"   상태 코드: {response.status_code}")
                if response.status_code == 200:
                    user_info = response.json()
                    print(f"   사용자 정보:")
                    print(f"     - ID: {user_info.get('id')}")
                    print(f"     - Email: {user_info.get('email')}")
                    print(f"     - Nickname: {user_info.get('nickname')}")
                    print(f"     - Provider: {user_info.get('social_provider')}")
                    print("   ✅ 사용자 정보 조회 성공\n")
                else:
                    print(f"   ❌ 에러: {response.json()}\n")
            except Exception as e:
                print(f"   ❌ 에러: {e}\n")
            
            # 6. 인증된 상태에서 메아리 API 호출
            print("6. 인증된 상태에서 메아리 세션 생성...")
            try:
                response = await client.post(
                    f"{API_URL}/api/v1/meari/sessions",
                    json={
                        "selected_tag_id": 2,
                        "user_context": "번아웃으로 힘든 상황입니다"
                    },
                    cookies=cookies
                )
                print(f"   상태 코드: {response.status_code}")
                if response.status_code == 201:
                    result = response.json()
                    print(f"   세션 ID: {result.get('session_id')}")
                    print(f"   세션 타입: {result.get('session_type')}")
                    print("   ✅ 메아리 세션 생성 성공\n")
                else:
                    print(f"   응답: {response.text}\n")
            except Exception as e:
                print(f"   ❌ 에러: {e}\n")
            
            # 7. 로그아웃
            print("7. 로그아웃...")
            try:
                response = await client.post(f"{API_URL}/auth/logout", cookies=cookies)
                print(f"   상태 코드: {response.status_code}")
                print(f"   응답: {response.json()}")
                print("   ✅ 로그아웃 성공\n")
            except Exception as e:
                print(f"   ❌ 에러: {e}\n")
            
            # 8. 로그아웃 후 사용자 정보 조회 (실패해야 함)
            print("8. 로그아웃 후 사용자 정보 조회...")
            try:
                response = await client.get(f"{API_URL}/auth/me", cookies=cookies)
                print(f"   상태 코드: {response.status_code}")
                assert response.status_code == 401, "로그아웃 후 401이 반환되어야 합니다"
                print("   ✅ 로그아웃 확인 완료\n")
            except Exception as e:
                print(f"   ❌ 에러: {e}\n")


if __name__ == "__main__":
    print("\n백엔드 서버가 실행 중인지 확인하세요.")
    print("실행 명령: uvicorn app.main:app --reload --port 8001\n")
    
    asyncio.run(test_auth_flow())