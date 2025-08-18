"""
Milvus 컬렉션 생성 및 데이터 임베딩 스크립트
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.data.vector_store import VectorStore
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.news import NewsQuote
from app.models.policy import YouthPolicy


async def main():
    """메인 함수"""
    
    # VectorStore 초기화
    print("Milvus 연결 중...")
    vector_store = VectorStore()
    
    # 1. 컬렉션 생성
    print("\n1. 컬렉션 생성 중...")
    quotes_collection = vector_store.create_quotes_collection()
    print(f"  - meari_quotes 컬렉션 생성 완료")
    
    policies_collection = vector_store.create_policies_collection()
    print(f"  - meari_policies 컬렉션 생성 완료")
    
    # 2. 데이터 로드
    async with AsyncSessionLocal() as db:
        # 인용문 데이터
        print("\n2. 인용문 데이터 로드 중...")
        stmt = select(NewsQuote)
        result = await db.execute(stmt)
        quotes = result.scalars().all()
        print(f"  - {len(quotes)}개 인용문 로드 완료")
        
        # 정책 데이터
        print("\n3. 정책 데이터 로드 중...")
        stmt = select(YouthPolicy)
        result = await db.execute(stmt)
        policies = result.scalars().all()
        print(f"  - {len(policies)}개 정책 로드 완료")
    
    # 3. 인용문 임베딩 및 저장
    if quotes:
        print("\n4. 인용문 벡터화 및 저장 중...")
        quotes_data = [
            {
                "id": q.id,
                "news_id": q.news_id,
                "quote_text": q.quote_text,
                "speaker": q.speaker or "",
                "tag_id": q.tag_id or 0
            }
            for q in quotes
        ]
        
        inserted = await vector_store.insert_quotes(quotes_data, batch_size=50)  # 배치 크기 50으로
        print(f"  - {inserted}개 인용문 벡터 저장 완료")
    
    # 4. 정책 임베딩 및 저장
    if policies:
        print("\n5. 정책 벡터화 및 저장 중...")
        policies_data = [
            {
                "policy_id": p.policy_id,
                "policy_name": p.policy_name,
                "support_content": p.support_content,
                "application_url": p.application_url or "",
                "organization": p.organization or ""
            }
            for p in policies
        ]
        
        inserted = await vector_store.insert_policies(policies_data, batch_size=50)  # 배치 크기 50으로
        print(f"  - {inserted}개 정책 벡터 저장 완료")
    
    print("\n✅ 모든 작업 완료!")
    
    # 5. 테스트 검색
    print("\n테스트 검색 실행 중...")
    
    # 인용문 검색 테스트
    test_results = await vector_store.search_quotes("번아웃", top_k=3)
    print("\n번아웃 관련 인용문 검색 결과:")
    for i, result in enumerate(test_results, 1):
        print(f"{i}. (유사도: {result['score']:.3f}) {result['quote_text'][:50]}...")
    
    # 정책 검색 테스트
    test_results = await vector_store.search_policies("청년 취업 지원", top_k=3)
    print("\n청년 취업 지원 정책 검색 결과:")
    for i, result in enumerate(test_results, 1):
        print(f"{i}. (유사도: {result['score']:.3f}) {result['policy_name']}")


if __name__ == "__main__":
    asyncio.run(main())