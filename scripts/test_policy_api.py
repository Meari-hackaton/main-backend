"""
청년정책 API 연결 테스트
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.data.youth_policy_client import YouthPolicyClient


async def test_api():
    """API 연결 및 데이터 수집 테스트"""
    
    print("청년정책 API 테스트 시작...")
    print("=" * 60)
    
    try:
        async with YouthPolicyClient() as client:
            # 첫 페이지 10개만 테스트
            print("\n1. API 연결 테스트 (첫 10개 정책)...")
            result = await client.get_policy_list(1, 10)
            
            print(f"✓ 전체 정책 수: {result['total_count']}개")
            print(f"✓ 수집된 정책: {len(result['policies'])}개")
            
            if result["policies"]:
                # 첫 번째 정책 상세 표시
                first = result["policies"][0]
                print(f"\n2. 첫 번째 정책 상세:")
                print(f"- ID: {first.get('bizId')}")
                print(f"- 정책명: {first.get('polyBizSjnm')}")
                print(f"- 기관: {first.get('cnsgNmor')}")
                print(f"- 연령: {first.get('ageInfo')}")
                print(f"- 신청기간: {first.get('rqutPrdCn', '')[:50]}...")
                
                # 데이터 가공 테스트
                print(f"\n3. 데이터 가공 테스트:")
                processed = client.process_policy_data(first)
                print(f"- policy_id: {processed['policy_id']}")
                print(f"- policy_name: {processed['policy_name']}")
                print(f"- organization: {processed['organization']}")
                print(f"- application_url: {processed['application_url'][:50]}...")
                
                # 지원 내용 일부 표시
                if processed['support_content']:
                    print(f"- support_content (100자): {processed['support_content'][:100]}...")
                
                print("\n✓ API 테스트 성공!")
            else:
                print("⚠ 정책 데이터가 비어있습니다.")
                
    except Exception as e:
        print(f"\n✗ API 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api())