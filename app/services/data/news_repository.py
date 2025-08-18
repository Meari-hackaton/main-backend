"""
뉴스 데이터 저장 Repository
빅카인즈에서 수집한 뉴스를 PostgreSQL에 저장
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.news import News
from app.models.tag import Tag
from app.core.database import async_session


class NewsRepository:
    """뉴스 데이터 저장 관리"""
    
    @staticmethod
    async def get_tag_by_name(session: AsyncSession, tag_name: str) -> Optional[Tag]:
        """태그 이름으로 태그 조회"""
        result = await session.execute(
            select(Tag).where(Tag.name == tag_name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def save_news(news_data: Dict, tag_name: str) -> bool:
        """
        뉴스 데이터 저장
        
        Args:
            news_data: 빅카인즈에서 수집한 뉴스 데이터
            tag_name: 태그 이름
        
        Returns:
            저장 성공 여부
        """
        async with async_session() as session:
            try:
                # 태그 조회
                tag = await NewsRepository.get_tag_by_name(session, tag_name)
                if not tag:
                    print(f"경고: '{tag_name}' 태그를 찾을 수 없습니다")
                    return False
                
                # 중복 체크
                existing = await session.execute(
                    select(News).where(News.news_id == news_data["news_id"])
                )
                if existing.scalar_one_or_none():
                    print(f"뉴스 {news_data['news_id']}는 이미 존재합니다")
                    return False
                
                # 날짜 파싱
                published_at = datetime.strptime(
                    news_data["published_at"], 
                    "%Y-%m-%d %H:%M:%S"
                )
                
                # News 객체 생성
                news = News(
                    news_id=news_data["news_id"],
                    title=news_data["title"],
                    content=news_data.get("content", ""),
                    provider=news_data["provider"],
                    published_at=published_at,
                    link_url=news_data.get("provider_link_page", ""),
                    category_codes=news_data.get("category", []),
                    tag_id=tag.id
                )
                
                session.add(news)
                await session.commit()
                return True
                
            except Exception as e:
                print(f"뉴스 저장 중 오류: {e}")
                await session.rollback()
                return False
    
    @staticmethod
    async def bulk_save_news(news_list: List[Dict]) -> Dict[str, int]:
        """
        뉴스 데이터 일괄 저장
        
        Args:
            news_list: 뉴스 데이터 리스트
        
        Returns:
            저장 통계 (성공/실패/중복 개수)
        """
        stats = {"success": 0, "failed": 0, "duplicate": 0}
        
        async with async_session() as session:
            for news_data in news_list:
                try:
                    tag_name = news_data.get("tag_name")
                    if not tag_name:
                        stats["failed"] += 1
                        continue
                    
                    # 태그 조회
                    tag = await NewsRepository.get_tag_by_name(session, tag_name)
                    if not tag:
                        print(f"경고: '{tag_name}' 태그를 찾을 수 없습니다")
                        stats["failed"] += 1
                        continue
                    
                    # 중복 체크
                    existing = await session.execute(
                        select(News).where(News.news_id == news_data["news_id"])
                    )
                    if existing.scalar_one_or_none():
                        stats["duplicate"] += 1
                        continue
                    
                    # 날짜 파싱
                    published_at = datetime.strptime(
                        news_data["published_at"], 
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    # News 객체 생성
                    news = News(
                        news_id=news_data["news_id"],
                        title=news_data["title"],
                        content=news_data.get("content", ""),
                        provider=news_data["provider"],
                        published_at=published_at,
                        link_url=news_data.get("provider_link_page", ""),
                        category_codes=news_data.get("category", []),
                        tag_id=tag.id
                    )
                    
                    session.add(news)
                    stats["success"] += 1
                    
                except Exception as e:
                    print(f"뉴스 {news_data.get('news_id')} 저장 실패: {e}")
                    stats["failed"] += 1
            
            # 일괄 커밋
            try:
                await session.commit()
                print(f"\n저장 완료: 성공 {stats['success']}개, 중복 {stats['duplicate']}개, 실패 {stats['failed']}개")
            except Exception as e:
                print(f"커밋 실패: {e}")
                await session.rollback()
                stats["failed"] += stats["success"]
                stats["success"] = 0
        
        return stats
    
    @staticmethod
    async def get_news_count_by_tag() -> Dict[str, int]:
        """태그별 뉴스 개수 조회"""
        async with async_session() as session:
            result = await session.execute(
                select(Tag.name, News.tag_id)
                .join(News, Tag.id == News.tag_id)
                .group_by(Tag.name, News.tag_id)
            )
            
            counts = {}
            for row in result:
                tag_name = row[0]
                # 각 태그별 뉴스 개수 조회
                count_result = await session.execute(
                    select(News).where(News.tag_id == row[1])
                )
                counts[tag_name] = len(count_result.scalars().all())
            
            return counts