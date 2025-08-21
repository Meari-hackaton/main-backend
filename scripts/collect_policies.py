"""
청년정책 데이터 수집 실행 스크립트
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from app.services.data.youth_policy_client import YouthPolicyClient
from app.services.data.policy_repository import PolicyRepository
from app.db.init_db import init_db


async def collect_all_policies():
    """모든 청년정책 수집 및 저장"""
    
    print("=" * 60)
    print("청년정책 데이터 수집 시작")
    print("=" * 60)
    
    # DB 테이블 확인
    print("\n1. DB 테이블 확인...")
    await init_db()
    
    # 기존 정책 개수 확인
    existing_count = await PolicyRepository.get_policy_count()
    print(f"기존 저장된 정책: {existing_count}개")
    
    # 청년정책 API 클라이언트 초기화
    print("\n2. 청년정책 API 클라이언트 초기화...")
    
    async with YouthPolicyClient() as client:
        # 전체 정책 수집
        print("\n3. 정책 데이터 수집 중...")
        raw_policies = await client.collect_all_policies()
        
        if not raw_policies:
            print("수집된 정책이 없습니다.")
            return
        
        # 데이터 가공
        print(f"\n4. {len(raw_policies)}개 정책 데이터 가공 중...")
        processed_policies = []
        
        for raw_policy in raw_policies:
            processed = client.process_policy_data(raw_policy)
            if processed["policy_id"]:  # 유효한 정책 ID가 있는 경우만
                processed_policies.append(processed)
        
        print(f"가공 완료: {len(processed_policies)}개")
        
        # DB 저장
        print("\n5. PostgreSQL 저장 중...")
        stats = await PolicyRepository.bulk_save_policies(processed_policies)
        
        print(f"\n저장 결과:")
        print(f"- 신규 저장: {stats['success']}개")
        print(f"- 업데이트: {stats['duplicate_updated']}개")
        print(f"- 실패: {stats['failed']}개")
    
    # 최종 통계
    final_count = await PolicyRepository.get_policy_count()
    print("\n" + "=" * 60)
    print("청년정책 수집 완료!")
    print(f"총 저장된 정책: {final_count}개")
    print("=" * 60)


async def show_sample_policies(limit: int = 5):
    """샘플 정책 데이터 확인"""
    
    policies = await PolicyRepository.get_all_policies()
    
    print(f"\n저장된 정책 샘플 (최신 {limit}개):")
    print("=" * 60)
    
    for i, policy in enumerate(policies[:limit], 1):
        print(f"\n[{i}] {policy.policy_name}")
        print(f"- ID: {policy.policy_id}")
        print(f"- 기관: {policy.organization}")
        print(f"- 대상: {policy.target_age}")
        print(f"- 신청기간: {policy.application_period}")
        print(f"- URL: {policy.application_url[:50]}...")
        
        # 지원내용 일부만 표시
        if policy.support_content:
            content_preview = policy.support_content[:150]
            print(f"- 내용: {content_preview}...")


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    
    # 환경변수 로드
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="청년정책 데이터 수집")
    parser.add_argument(
        "--show",
        action="store_true",
        help="저장된 정책 샘플 표시"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="표시할 샘플 개수 (기본: 5)"
    )
    
    args = parser.parse_args()
    
    if args.show:
        asyncio.run(show_sample_policies(args.limit))
    else:
        asyncio.run(collect_all_policies())