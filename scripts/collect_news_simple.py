"""
빅카인즈 뉴스 수집 실행 스크립트 (간소화 버전)
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from app.services.data.bigkinds_client import BigKindsClient
from app.core.bigkinds_config import BIGKINDS_TAG_CONFIG
from app.core.database import AsyncSessionLocal
from app.models.news import News
from app.models.tag import Tag
from sqlalchemy import select


async def collect_all_news():
    """모든 태그에 대한 뉴스 수집"""
    
    print("=" * 60)
    print("빅카인즈 뉴스 수집 시작")
    print("=" * 60)
    
    client = BigKindsClient()
    
    # DB에서 중분류 태그 가져오기
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tag).where(Tag.parent_id != None)
        )
        tags = result.scalars().all()
        
        print(f"\n수집할 태그: {len(tags)}개")
        for tag in tags:
            print(f"  - {tag.name} (ID: {tag.id})")
    
    # 날짜 범위 설정 (최근 5년)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*5)
    
    total_news_count = 0
    
    for tag in tags:
        print(f"\n[{tag.name}] 뉴스 수집 시작...")
        
        # 태그별 쿼리 가져오기
        query = BIGKINDS_TAG_CONFIG[tag.name]['query']
        category_codes = BIGKINDS_TAG_CONFIG[tag.name]['category_codes']
        
        # 검색 요청
        search_result = await client.search_news(
            query=query,
            start_date=start_date,
            end_date=end_date,
            category_codes=category_codes,
            sort_method=1,  # 정확도순
            return_count=100
        )
        
        if not search_result:
            print(f"  ❌ 검색 실패")
            continue
            
        news_ids = search_result.get('news_ids', [])
        print(f"  - 검색 결과: {len(news_ids)}개")
        
        if not news_ids:
            continue
        
        # 뉴스 상세 정보 수집 (100개씩 배치)
        for i in range(0, len(news_ids), 100):
            batch_ids = news_ids[i:i+100]
            print(f"  - 배치 {i//100 + 1} 수집 중 ({len(batch_ids)}개)...")
            
            detail_result = await client.get_news_detail(batch_ids)
            
            if not detail_result:
                print(f"    ❌ 상세 정보 수집 실패")
                continue
            
            news_list = detail_result.get('news', [])
            
            # DB에 저장
            async with AsyncSessionLocal() as session:
                for news_data in news_list:
                    # 중복 체크
                    existing = await session.execute(
                        select(News).where(News.news_id == news_data['news_id'])
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    # 새 뉴스 저장
                    news = News(
                        news_id=news_data['news_id'],
                        title=news_data.get('title', ''),
                        content=news_data.get('content', '')[:200],  # 200자 제한
                        hilight=news_data.get('hilight', ''),
                        tms_raw_stream=news_data.get('tms_raw_stream', ''),
                        provider=news_data.get('provider_name', ''),
                        published_at=datetime.strptime(
                            news_data.get('published_at', '20200101'), 
                            '%Y%m%d'
                        ),
                        link_url=news_data.get('provider_link_page', ''),
                        category_codes=news_data.get('category_list', []),
                        tag_id=tag.id
                    )
                    session.add(news)
                
                await session.commit()
                print(f"    ✅ {len(news_list)}개 저장 완료")
        
        total_news_count += len(news_ids)
    
    print(f"\n총 {total_news_count}개 뉴스 수집 완료!")


if __name__ == "__main__":
    asyncio.run(collect_all_news())