"""
빅카인즈 인용문 API를 활용한 인용문 추출 서비스
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.news import News, NewsQuote
from app.core.bigkinds_config import BIGKINDS_TAG_CONFIG
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class QuoteExtractor:
    """빅카인즈 인용문 API를 활용한 인용문 추출"""
    
    BASE_URL = "https://tools.kinds.or.kr"
    
    def __init__(self):
        self.access_key = os.getenv("BIGKINDS_ACCESS_KEY")
        if not self.access_key:
            raise ValueError("BIGKINDS_ACCESS_KEY 환경변수가 설정되지 않았습니다")
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def search_quotations(
        self,
        query: str,
        category_codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        size: int = 100
    ) -> Dict:
        """
        인용문 검색 API 호출
        
        Args:
            query: 검색 쿼리 (뉴스 수집과 동일)
            category_codes: 카테고리 코드 리스트
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            page: 페이지 번호
            size: 페이지당 결과 수 (최대 100)
        
        Returns:
            인용문 검색 결과
        """
        if not start_date:
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
                "provider_subject": [],
                "subject_info": [],
                "subject_info1": [],
                "subject_info2": [],
                "subject_info3": [],
                "subject_info4": [],
                "sort": {"date": "desc"},
                "hilight": 200,
                "return_from": (page - 1) * size,
                "return_size": size,
                "fields": [
                    "news_id",
                    "source",
                    "quotation",
                    "published_at",
                    "provider",
                    "category"
                ]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/search/quotation",
                headers=self.headers,
                json=search_params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"인용문 API 요청 실패: {response.status} - {error_text}")
                    return {"documents": [], "total_hits": 0}
                
                result = await response.json()
                return result.get("return_object", {})
    
    async def collect_quotes_for_tag(
        self,
        tag_name: str,
        tag_id: int,
        target_count: int = 100
    ) -> List[Dict]:
        """
        특정 태그에 대한 인용문 수집
        
        Args:
            tag_name: 태그 이름
            tag_id: 태그 ID
            target_count: 수집할 인용문 개수 (기본 100개)
        
        Returns:
            수집된 인용문 리스트
        """
        config = BIGKINDS_TAG_CONFIG.get(tag_name, {})
        query = config.get("query", "")
        category_codes = config.get("categories", [])
        
        if not query:
            logger.warning(f"태그 '{tag_name}'에 대한 쿼리가 정의되지 않았습니다")
            return []
        
        print(f"\n[{tag_name}] 인용문 수집 시작...")
        all_quotes = []
        page = 1
        
        while len(all_quotes) < target_count:
            print(f"  - 페이지 {page} 검색 중...")
            
            result = await self.search_quotations(
                query=query,
                category_codes=category_codes,
                page=page,
                size=min(100, target_count - len(all_quotes))
            )
            
            documents = result.get("documents", [])
            total_hits = result.get("total_hits", 0)
            
            if not documents:
                print(f"  - 더 이상 검색 결과가 없습니다")
                break
            
            for doc in documents:
                quote_data = {
                    "news_id": doc.get("news_id"),
                    "source": doc.get("source", ""),
                    "quotation": doc.get("quotation", ""),
                    "published_at": doc.get("published_at"),
                    "provider": doc.get("provider"),
                    "tag_id": tag_id,
                    "tag_name": tag_name
                }
                all_quotes.append(quote_data)
            
            print(f"  - 현재까지 {len(all_quotes)}개 수집 (전체: {total_hits}개)")
            
            if len(all_quotes) >= target_count or len(documents) < 100:
                break
            
            page += 1
            await asyncio.sleep(0.5)
        
        print(f"[{tag_name}] 총 {len(all_quotes)}개 인용문 수집 완료")
        return all_quotes[:target_count]
    
    async def save_quotes_to_db(
        self,
        db: AsyncSession,
        quotes: List[Dict]
    ) -> int:
        """
        수집된 인용문을 DB에 저장
        
        Args:
            db: 데이터베이스 세션
            quotes: 저장할 인용문 리스트
        
        Returns:
            저장된 인용문 개수
        """
        saved_count = 0
        
        for quote_data in quotes:
            # 중복 체크
            stmt = select(NewsQuote).where(
                NewsQuote.news_id == quote_data["news_id"],
                NewsQuote.quote_text == quote_data["quotation"]
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                continue
            
            # NewsQuote 생성
            news_quote = NewsQuote(
                news_id=quote_data["news_id"],
                quote_text=quote_data["quotation"],
                speaker=quote_data["source"] if quote_data["source"] else None,
                quote_type="direct",
                extraction_method="api",
                tag_id=quote_data["tag_id"]
            )
            
            db.add(news_quote)
            saved_count += 1
        
        if saved_count > 0:
            await db.commit()
            logger.info(f"{saved_count}개 인용문 저장 완료")
        
        return saved_count
    
    async def collect_all_tag_quotes(
        self,
        db: AsyncSession,
        tags: List[Dict],
        quotes_per_tag: int = 100
    ):
        """
        모든 태그에 대한 인용문 수집 및 저장
        
        Args:
            db: 데이터베이스 세션
            tags: 태그 리스트 (id, name 포함)
            quotes_per_tag: 태그당 수집할 인용문 개수 (기본 100개)
        """
        total_saved = 0
        
        for tag in tags:
            tag_id = tag["id"]
            tag_name = tag["name"]
            
            # 인용문 수집
            quotes = await self.collect_quotes_for_tag(
                tag_name=tag_name,
                tag_id=tag_id,
                target_count=quotes_per_tag
            )
            
            # DB 저장
            if quotes:
                saved = await self.save_quotes_to_db(db, quotes)
                total_saved += saved
                print(f"  - DB에 {saved}개 저장")
            
            # API 부하 방지
            await asyncio.sleep(1)
        
        print(f"\n전체 수집 완료: 총 {total_saved}개 인용문 저장")