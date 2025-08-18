"""
빅카인즈 API 클라이언트
뉴스 데이터 수집을 위한 API 호출 및 데이터 처리
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
from app.core.config import settings


class BigKindsClient:
    """빅카인즈 API 클라이언트"""
    
    BASE_URL = "https://www.bigkinds.or.kr/api"
    
    def __init__(self):
        self.access_key = os.getenv("BIGKINDS_ACCESS_KEY")
        if not self.access_key:
            raise ValueError("BIGKINDS_ACCESS_KEY 환경변수가 설정되지 않았습니다")
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def search_news(
        self, 
        query: str,
        category_codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        size: int = 100
    ) -> Dict:
        """
        뉴스 검색 - 1단계: 뉴스 ID 수집
        
        Args:
            query: 검색 쿼리
            category_codes: 카테고리 코드 리스트
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            page: 페이지 번호
            size: 페이지당 결과 수 (최대 100)
        
        Returns:
            검색 결과 (news_ids 포함)
        """
        if not start_date:
            # 기본값: 5년 전부터
            start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        search_params = {
            "access_key": self.access_key,
            "argument": {
                "query": query,
                "published_at": {
                    "from": start_date,
                    "until": end_date
                },
                "category": category_codes,
                "category_incident": [],
                "byline": "",
                "provider": [],
                "subject_info": [],
                "subject_info1": [],
                "subject_info2": [],
                "subject_info3": [],
                "subject_info4": [],
                "sort": {"date": "desc"},  # 최신순 정렬
                "hilight": 200,
                "return_from": (page - 1) * size,
                "return_size": size,
                "fields": ["news_id", "title", "provider", "published_at"]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/news/v2/search",
                headers=self.headers,
                json=search_params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API 요청 실패: {response.status} - {error_text}")
                
                result = await response.json()
                return result.get("return_object", {})
    
    async def get_news_detail(self, news_ids: List[str]) -> List[Dict]:
        """
        뉴스 상세 조회 - 2단계: 전체 본문 수집
        
        Args:
            news_ids: 뉴스 ID 리스트 (최대 100개)
        
        Returns:
            뉴스 상세 정보 리스트
        """
        if len(news_ids) > 100:
            raise ValueError("한 번에 최대 100개까지만 조회 가능합니다")
        
        detail_params = {
            "access_key": self.access_key,
            "argument": {
                "news_ids": news_ids,
                "fields": [
                    "content",
                    "byline",
                    "category",
                    "category_incident",
                    "images",
                    "provider_subject",
                    "provider_news_id",
                    "publisher_code"
                ]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/news/v2/detail",
                headers=self.headers,
                json=detail_params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API 요청 실패: {response.status} - {error_text}")
                
                result = await response.json()
                return result.get("return_object", {}).get("documents", [])
    
    async def collect_news_for_tag(
        self,
        tag_name: str,
        query: str,
        category_codes: List[str],
        target_count: int = 100
    ) -> List[Dict]:
        """
        특정 태그에 대한 뉴스 수집 (검색 + 상세 조회)
        
        Args:
            tag_name: 태그 이름
            query: 검색 쿼리
            category_codes: 카테고리 코드 리스트
            target_count: 수집할 뉴스 개수
        
        Returns:
            수집된 뉴스 리스트
        """
        print(f"\n[{tag_name}] 뉴스 수집 시작...")
        all_news = []
        page = 1
        
        while len(all_news) < target_count:
            # 1단계: 뉴스 ID 검색
            print(f"  - 페이지 {page} 검색 중...")
            search_result = await self.search_news(
                query=query,
                category_codes=category_codes,
                page=page,
                size=min(100, target_count - len(all_news))
            )
            
            documents = search_result.get("documents", [])
            if not documents:
                print(f"  - 더 이상 검색 결과가 없습니다")
                break
            
            # 뉴스 ID 추출
            news_ids = [doc["news_id"] for doc in documents]
            
            # 2단계: 상세 정보 조회
            print(f"  - {len(news_ids)}개 뉴스 상세 정보 조회 중...")
            detailed_news = await self.get_news_detail(news_ids)
            
            # 기본 정보와 상세 정보 병합
            for doc, detail in zip(documents, detailed_news):
                merged = {**doc, **detail}
                merged["tag_name"] = tag_name
                all_news.append(merged)
            
            print(f"  - 현재까지 {len(all_news)}개 수집 완료")
            
            if len(documents) < 100:
                break
            
            page += 1
            await asyncio.sleep(0.5)  # API 부하 방지
        
        print(f"[{tag_name}] 총 {len(all_news)}개 뉴스 수집 완료")
        return all_news[:target_count]