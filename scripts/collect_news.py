"""
빅카인즈 뉴스 수집 실행 스크립트
9개 태그별로 100건씩 뉴스 수집
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from app.services.data.bigkinds_client import BigKindsClient
from app.services.data.news_repository import NewsRepository
from app.core.bigkinds_config import BIGKINDS_TAG_CONFIG
from app.db.seed_tags import seed_tags
from app.db.init_db import init_db


async def collect_all_news():
    """모든 태그에 대한 뉴스 수집"""
    
    print("=" * 60)
    print("빅카인즈 뉴스 수집 시작")
    print("=" * 60)
    
    # DB 초기화 (테이블 생성)
    print("\n1. DB 테이블 확인...")
    await init_db()
    
    # 태그 초기화
    print("\n2. 태그 데이터 초기화...")
    await seed_tags()
    
    # 빅카인즈 클라이언트 초기화
    print("\n3. 빅카인즈 API 클라이언트 초기화...")
    try:
        client = BigKindsClient()
    except ValueError as e:
        print(f"오류: {e}")
        print("BIGKINDS_ACCESS_KEY 환경변수를 설정해주세요")
        return
    
    # 각 태그별로 뉴스 수집
    print("\n4. 뉴스 수집 시작...")
    total_collected = 0
    total_saved = 0
    
    for tag_name, config in BIGKINDS_TAG_CONFIG.items():
        print(f"\n{'='*40}")
        print(f"태그: {tag_name}")
        print(f"쿼리: {config['query'][:50]}...")
        print(f"카테고리: {config['categories']}")
        print(f"{'='*40}")
        
        try:
            # 뉴스 수집
            news_list = await client.collect_news_for_tag(
                tag_name=tag_name,
                query=config["query"],
                category_codes=config["categories"],
                target_count=100  # 태그당 100건
            )
            
            total_collected += len(news_list)
            
            # DB 저장
            if news_list:
                print(f"\n[{tag_name}] DB 저장 중...")
                stats = await NewsRepository.bulk_save_news(news_list)
                total_saved += stats["success"]
                
                print(f"[{tag_name}] 저장 완료: "
                      f"성공 {stats['success']}건, "
                      f"중복 {stats['duplicate']}건, "
                      f"실패 {stats['failed']}건")
            
            # API 부하 방지를 위한 대기
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"[{tag_name}] 수집 중 오류 발생: {e}")
            continue
    
    # 최종 통계
    print("\n" + "=" * 60)
    print("뉴스 수집 완료!")
    print(f"총 수집: {total_collected}건")
    print(f"총 저장: {total_saved}건")
    
    # 태그별 저장된 뉴스 개수 확인
    print("\n태그별 저장된 뉴스 개수:")
    counts = await NewsRepository.get_news_count_by_tag()
    for tag_name, count in counts.items():
        print(f"  - {tag_name}: {count}건")
    print("=" * 60)


async def collect_specific_tag(tag_name: str):
    """특정 태그에 대한 뉴스만 수집"""
    
    if tag_name not in BIGKINDS_TAG_CONFIG:
        print(f"오류: '{tag_name}'은(는) 유효한 태그가 아닙니다")
        print(f"사용 가능한 태그: {list(BIGKINDS_TAG_CONFIG.keys())}")
        return
    
    print(f"\n'{tag_name}' 태그 뉴스 수집 시작...")
    
    # DB 초기화
    await init_db()
    await seed_tags()
    
    # 빅카인즈 클라이언트
    try:
        client = BigKindsClient()
    except ValueError as e:
        print(f"오류: {e}")
        return
    
    config = BIGKINDS_TAG_CONFIG[tag_name]
    
    # 뉴스 수집
    news_list = await client.collect_news_for_tag(
        tag_name=tag_name,
        query=config["query"],
        category_codes=config["categories"],
        target_count=100
    )
    
    # DB 저장
    if news_list:
        print(f"\nDB 저장 중...")
        stats = await NewsRepository.bulk_save_news(news_list)
        print(f"저장 완료: 성공 {stats['success']}건, "
              f"중복 {stats['duplicate']}건, "
              f"실패 {stats['failed']}건")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="빅카인즈 뉴스 수집")
    parser.add_argument(
        "--tag",
        type=str,
        help="특정 태그만 수집 (미지정시 전체 수집)"
    )
    
    args = parser.parse_args()
    
    if args.tag:
        asyncio.run(collect_specific_tag(args.tag))
    else:
        asyncio.run(collect_all_news())