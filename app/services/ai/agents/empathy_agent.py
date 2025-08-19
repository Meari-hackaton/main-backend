from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer
import numpy as np
import os


class EmpathyCard(BaseModel):
    """공감 카드 응답"""
    content: str = Field(description="공감 카드 내용")
    quotes_used: List[Dict[str, Any]] = Field(description="사용된 인용문 목록")
    emotion_keywords: List[str] = Field(description="감정 키워드")


class EmpathyAgent:
    """Vector RAG 기반 공감 카드 생성 에이전트"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.7,  # 공감적 응답을 위해 높은 temperature
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Milvus 연결
        self._connect_milvus()
        
        # 임베딩 모델 로드
        self.embedding_model = SentenceTransformer('nlpai-lab/KURE-v1')
        
        # 프롬프트 설정
        self.prompt = self._create_prompt()
    
    def _connect_milvus(self):
        """Milvus 연결"""
        connections.connect(
            alias="default",
            uri=os.getenv("MILVUS_URI"),
            token=os.getenv("MILVUS_TOKEN")
        )
        
        # 인용문 컬렉션 로드
        self.quotes_collection = Collection("meari_quotes")
        self.quotes_collection.load()
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """공감 카드 생성 프롬프트"""
        
        system_message = """당신은 청년들의 마음을 깊이 이해하는 공감 상담사입니다.
제공된 인용문들을 바탕으로 따뜻하고 진정성 있는 공감 메시지를 작성하세요.

## 작성 원칙:
1. 서술형으로 자연스럽게 작성 (1-2문단)
2. 인용문의 감정을 깊이 공감하며 반영
3. "당신의 마음이 느껴져요", "충분히 그럴 수 있어요" 같은 공감 표현 사용
4. 비판이나 조언 없이 순수한 공감과 위로만 전달
5. 희망적이지만 현실적인 톤 유지

## 피해야 할 표현:
- "힘내세요", "화이팅" 같은 피상적 응원
- "~해보세요", "~하면 좋아요" 같은 조언
- 문제를 축소하거나 무시하는 표현
- 이모티콘이나 과도한 감탄사"""
        
        human_template = """다음 인용문들을 읽고 공감 카드를 작성하세요:

{quotes}

사용자 상황: {user_context}

공감 카드:"""
        
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
        results = self.quotes_collection.search(
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
    
    def generate_empathy_card(
        self, 
        quotes: List[Dict[str, Any]], 
        user_context: str
    ) -> EmpathyCard:
        """공감 카드 생성"""
        
        # 인용문 포맷팅
        quotes_text = "\n\n".join([
            f"인용문 {i+1}: \"{quote['text']}\""
            for i, quote in enumerate(quotes[:5])  # 최대 5개
        ])
        
        # LLM으로 공감 카드 생성
        chain = self.prompt | self.llm
        response = chain.invoke({
            "quotes": quotes_text,
            "user_context": user_context
        })
        
        # 감정 키워드 추출 (LLM 응답에서 추출하거나 기본값 사용)
        emotions = ["공감", "위로", "이해"]  # 기본 감정 키워드
        
        return EmpathyCard(
            content=response.content,
            quotes_used=quotes[:5],
            emotion_keywords=emotions
        )
    
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
        
        # 공감 카드 생성
        empathy_card = self.generate_empathy_card(quotes, user_context)
        
        # 상태 업데이트
        state["empathy_card"] = {
            "content": empathy_card.content,
            "quotes_used": empathy_card.quotes_used,
            "emotion_keywords": empathy_card.emotion_keywords
        }
        state["empathy_completed"] = True
        
        return state
    
    def close(self):
        """연결 종료"""
        connections.disconnect("default")