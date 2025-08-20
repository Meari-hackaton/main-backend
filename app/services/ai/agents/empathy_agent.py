from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models.news import News
from app.services.data.vector_store import get_quotes_collection
import numpy as np
import os


class QuoteCard(BaseModel):
    """개별 인용문 기반 공감 카드"""
    title: str = Field(description="카드 제목")
    content: str = Field(description="카드 내용 (200-300자)")
    quote_text: str = Field(description="사용된 인용문")
    speaker: Optional[str] = Field(description="발화자")
    news_id: Optional[str] = Field(description="관련 뉴스 ID")
    news_title: Optional[str] = Field(description="관련 뉴스 제목")
    news_provider: Optional[str] = Field(description="언론사")
    news_date: Optional[str] = Field(description="뉴스 날짜")
    news_link: Optional[str] = Field(description="뉴스 링크")
    emotion_keywords: List[str] = Field(description="감정 키워드 3개")

class EmpathyCards(BaseModel):
    """공감 카드 3종 세트"""
    cards: List[QuoteCard] = Field(description="3개의 공감 카드")


class EmpathyAgent:
    """Vector RAG 기반 공감 카드 생성 에이전트"""
    
    def __init__(self, api_key=None):
        # API 키가 제공되지 않으면 기본값 사용
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.7,  # 공감적 응답을 위해 높은 temperature
            google_api_key=api_key
        )
        
        # Milvus 컬렉션은 사용 시점에 가져오기
        self.quotes_collection = None
        
        # 임베딩 모델 로드
        self.embedding_model = SentenceTransformer('nlpai-lab/KURE-v1')
        
        # 프롬프트 설정
        self.prompt = self._create_prompt()
        
        # 동기 데이터베이스 연결 설정
        database_url = os.getenv("DATABASE_URL")
        if database_url and "asyncpg" in database_url:
            database_url = database_url.replace("postgresql+asyncpg", "postgresql")
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _get_collection(self):
        """Milvus 컬렉션 가져오기 (lazy loading)"""
        if self.quotes_collection is None:
            self.quotes_collection = get_quotes_collection()
        return self.quotes_collection
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """공감 카드 생성 프롬프트"""
        
        system_message = """당신은 청년들의 마음을 깊이 이해하는 공감 상담사입니다.
제공된 인용문들을 바탕으로 3개의 공감 카드를 작성하세요.

## 작성 원칙:
1. 각 인용문마다 하나의 카드로 작성 (200-300자)
2. 서로 다른 관점으로 공감 전달
3. 인용문의 감정을 깊이 공감하며 반영
4. 비판이나 조언 없이 순수한 공감과 위로만 전달
5. 희망적이지만 현실적인 톤 유지

## 응답 형식:
JSON 코드 블록 없이 순수한 JSON 배열만 응답하세요. 설명이나 추가 텍스트를 포함하지 마세요.

[{{"title": "같은 마음이 느껴져요", "content": "카드 내용", "emotion_keywords": ["키워드1", "키워드2", "키워드3"]}}, {{"title": "왜 그렇게 느껴지는지 알 것 같아요", "content": "카드 내용", "emotion_keywords": ["키워드1", "키워드2", "키워드3"]}}, {{"title": "당신만이 그런 것은 아니에요", "content": "카드 내용", "emotion_keywords": ["키워드1", "키워드2", "키워드3"]}}]"""
        
        human_template = """다음 3개의 인용문로 각각 다른 공감 카드를 작성하세요:

{quotes}

사용자 상황: {user_context}

위의 JSON 형식으로만 응답하세요. 다른 설명은 추가하지 마세요:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def search_similar_quotes(
        self, 
        user_context: str, 
        tag_ids: List[int] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """유사한 인용문 검색"""
        
        # 사용자 입력 임베딩
        user_embedding = self.embedding_model.encode(user_context)
        
        # 검색 파라미터
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        
        # 태그 필터 생성
        if tag_ids:
            expr = f"tag_id in {tag_ids}"
        else:
            expr = None
        
        # 벡터 검색
        collection = self._get_collection()
        results = collection.search(
            data=[user_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["quote_text", "speaker", "news_id", "tag_id"]
        )
        
        # 결과 정리
        quotes = []
        for hit in results[0]:
            quote_data = {
                "text": hit.entity.get("quote_text"),
                "speaker": hit.entity.get("speaker"),
                "news_id": hit.entity.get("news_id"),
                "tag_id": hit.entity.get("tag_id"),
                "similarity_score": hit.distance
            }
            quotes.append(quote_data)
        
        return quotes
    
    def _get_news_info_sync(self, news_ids: List[str]) -> Dict[str, Dict]:
        """뉴스 ID로 뉴스 정보 조회 (동기 버전)"""
        news_info = {}
        
        if not news_ids:
            return news_info
        
        with self.SessionLocal() as session:
            for news_id in news_ids:
                if news_id:
                    result = session.execute(
                        select(News).where(News.news_id == news_id)
                    )
                    news = result.scalar_one_or_none()
                    if news:
                        news_info[news_id] = {
                            "title": news.title,
                            "provider": news.provider,
                            "published_at": news.published_at.strftime("%Y년 %m월 %d일") if news.published_at else "",
                            "link_url": news.link_url
                        }
        return news_info
    
    def generate_empathy_cards(
        self, 
        quotes: List[Dict[str, Any]], 
        user_context: str
    ) -> List[QuoteCard]:
        """공감 카드 3개 생성"""
        
        # 상위 3개 인용문 선택
        top_quotes = quotes[:3]
        
        # 각 인용문에 대한 포맷팅
        quotes_text = "\n\n".join([
            f"인용문 {i+1}: \"{quote['text']}\"\n발화자: {quote.get('speaker', '알 수 없음')}"
            for i, quote in enumerate(top_quotes)
        ])
        
        # LLM으로 공감 카드 생성
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({
                "quotes": quotes_text,
                "user_context": user_context
            })
            
            # 응답 파싱
            import json
            import re
            
            content = response.content.strip()
            
            # 코드 블록 제거 (```json ... ``` 형태)
            content = re.sub(r'```json?\s*', '', content)
            content = re.sub(r'```\s*$', '', content)
            
            # 앞뒤 공백 제거
            content = content.strip()
            
            # JSON 파싱 시도
            try:
                if content.startswith('[') and content.endswith(']'):
                    cards_data = json.loads(content)
                else:
                    # JSON 배열 부분만 추출 시도
                    start_idx = content.find('[')
                    end_idx = content.rfind(']') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = content[start_idx:end_idx]
                        cards_data = json.loads(json_str)
                    else:
                        raise ValueError("JSON 배열을 찾을 수 없음")
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 실패: {e}")
                print(f"원본 응답: {content[:500]}...")
                raise ValueError(f"JSON 파싱 실패: {e}")
            
            # 뉴스 정보 조회
            news_ids = [q.get('news_id') for q in top_quotes if q.get('news_id')]
            news_info = self._get_news_info_sync(news_ids)
            
            # 카드 생성
            cards = []
            card_titles = [
                "같은 마음이 느껴져요",
                "왜 그렇게 느껴지는지 알 것 같아요",
                "당신만이 그런 것은 아니에요"
            ]
            
            for i, quote in enumerate(top_quotes):
                card_data = cards_data[i] if i < len(cards_data) else {}
                news_id = quote.get('news_id')
                ninfo = news_info.get(news_id, {})
                
                card = QuoteCard(
                    title=card_data.get("title", card_titles[i]),
                    content=card_data.get("content", f"{quote['text'][:100]}...에 대한 공감"),
                    quote_text=quote['text'],
                    speaker=quote.get('speaker'),
                    news_id=news_id,
                    news_title=ninfo.get("title"),
                    news_provider=ninfo.get("provider"),
                    news_date=ninfo.get("published_at"),
                    news_link=ninfo.get("link_url"),
                    emotion_keywords=card_data.get("emotion_keywords", ["공감", "위로", "이해"])
                )
                cards.append(card)
            
            return cards
            
        except Exception as e:
            print(f"카드 생성 실패: {e}")
            # 뉴스 정보를 먼저 조회
            news_ids = [q.get('news_id') for q in top_quotes if q.get('news_id')]
            news_info = self._get_news_info_sync(news_ids)
            return self._generate_default_cards(top_quotes, news_info)
    
    def _generate_default_cards(self, quotes: List[Dict[str, Any]], news_info: Dict[str, Dict] = None) -> List[QuoteCard]:
        """기본 공감 카드 생성"""
        if news_info is None:
            news_info = {}
            
        cards = []
        default_messages = [
            "비슷한 상황에 있는 많은 사람들이 이런 이야기를 하고 있어요. 당신의 마음이 충분히 이해됩니다.",
            "지금 그런 감정을 느끼는 것은 당연한 일입니다. 누구나 이런 상황에서는 비슷하게 느낄 거예요.",
            "혼자가 아니에요. 많은 사람들이 지금 이 순간에도 비슷한 어려움을 겪고 있고, 그들도 똑같이 힘든 감정을 느끼고 있습니다."
        ]
        card_titles = [
            "같은 마음이 느껴져요",
            "왜 그렇게 느껴지는지 알 것 같아요",
            "당신만이 그런 것은 아니에요"
        ]
        
        for i in range(3):
            quote = quotes[i] if i < len(quotes) else {"text": "", "news_id": None}
            news_id = quote.get('news_id')
            ninfo = news_info.get(news_id, {}) if news_id else {}
            
            card = QuoteCard(
                title=card_titles[i],
                content=default_messages[i],
                quote_text=quote.get('text', ''),
                speaker=quote.get('speaker'),
                news_id=news_id,
                news_title=ninfo.get("title"),
                news_provider=ninfo.get("provider"),
                news_date=ninfo.get("published_at"),
                news_link=ninfo.get("link_url"),
                emotion_keywords=["공감", "위로", "이해"]
            )
            cards.append(card)
        
        return cards
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        # 입력 추출
        user_context = state.get("user_context", "")
        tag_ids = state.get("tag_ids", [])
        
        # 유사 인용문 검색
        quotes = self.search_similar_quotes(
            user_context=user_context,
            tag_ids=tag_ids,
            top_k=7  # 여유있게 7개 검색
        )
        
        # 공감 카드 3개 생성
        cards = self.generate_empathy_cards(quotes, user_context)
        
        # 상태 업데이트 - 3개 카드를 하나의 content로 통합
        combined_content = "\n\n".join([
            f"### {card.title}\n{card.content}"
            for card in cards
        ])
        
        # quotes_used 구조 생성 (스키마 호환성 유지)
        quotes_used = [
            {
                "text": card.quote_text,
                "speaker": card.speaker,
                "news_id": card.news_id
            }
            for card in cards
        ]
        
        state["empathy_card"] = {
            "content": combined_content,
            "quotes_used": quotes_used,
            "emotion_keywords": cards[0].emotion_keywords if cards else [],
            "cards": [
                {
                    "title": card.title,
                    "content": card.content,
                    "quote_text": card.quote_text,
                    "speaker": card.speaker,
                    "news_id": card.news_id,
                    "news_title": card.news_title,
                    "news_provider": card.news_provider,
                    "news_date": card.news_date,
                    "news_link": card.news_link,
                    "emotion_keywords": card.emotion_keywords
                }
                for card in cards
            ]
        }
        state["empathy_completed"] = True
        
        return state
    
    def close(self):
        """연결 종료"""
        connections.disconnect("default")