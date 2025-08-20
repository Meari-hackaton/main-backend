from typing import Dict, Any, List, Optional, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.services.data.milvus_connection import get_policies_collection
from sentence_transformers import SentenceTransformer
from app.services.data.vector_store import get_policies_collection
import os
from concurrent.futures import ThreadPoolExecutor


class GrowthContent(BaseModel):
    """성장 콘텐츠 응답"""
    information: Dict[str, Any] = Field(description="정보 콘텐츠")
    experience: Dict[str, Any] = Field(description="경험 콘텐츠")
    support: Dict[str, Any] = Field(description="지원 콘텐츠")


class GrowthAgent:
    """3종 성장 콘텐츠 생성 에이전트"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.7,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Milvus 커렉션은 사용 시점에 가져오기
        self.policies_collection = None
        
        # 임베딩 모델
        self.embedding_model = SentenceTransformer('nlpai-lab/KURE-v1')
        
        # 프롬프트 설정
        self.info_prompt = self._create_info_prompt()
        self.exp_prompt = self._create_exp_prompt()
    
    def _get_collection(self):
        """Milvus 커렉션 가져오기 (lazy loading)"""
        if self.policies_collection is None:
            self.policies_collection = get_policies_collection()
        return self.policies_collection
    
    def _create_info_prompt(self) -> ChatPromptTemplate:
        """정보 검색 쿼리 생성 프롬프트"""
        
        system_message = """사용자 상황에 맞는 유용한 정보를 검색하고 요약하세요.

## 원칙:
1. 실용적이고 구체적인 정보
2. 신뢰할 수 있는 출처 우선
3. 최신 정보 위주
4. 핵심 내용 요약 + 출처 링크"""
        
        human_template = """상황: {user_context}

검색할 정보:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def _create_exp_prompt(self) -> ChatPromptTemplate:
        """리츄얼 제안 프롬프트"""
        
        system_message = """10분 이내 실천 가능한 리츄얼을 제안하세요.

## 원칙:
1. 즉시 실천 가능
2. 특별한 도구 불필요
3. 구체적인 방법 제시"""
        
        human_template = """상황: {user_context}

리츄얼 제안:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def search_relevant_policy(
        self,
        user_context: str,
        previous_policy_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """관련 정책 검색"""
        
        query_embedding = self.embedding_model.encode(user_context)
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        
        # 중복 제외
        expr = f"policy_id not in {previous_policy_ids}" if previous_policy_ids else None
        
        collection = self._get_collection()
        results = collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=5,
            expr=expr,
            output_fields=["policy_id", "policy_name", "support_content", "application_url", "organization"]
        )
        
        if results and len(results[0]) > 0:
            hit = results[0][0]
            return {
                "policy_id": hit.entity.get("policy_id"),
                "policy_name": hit.entity.get("policy_name"),
                "support_content": hit.entity.get("support_content"),
                "application_url": hit.entity.get("application_url"),
                "organization": hit.entity.get("organization")
            }
        return None
    
    def generate_information(self, user_context: str) -> Dict[str, Any]:
        """정보 검색 및 요약"""
        
        # 검색 쿼리 생성
        chain = self.info_prompt | self.llm
        query_response = chain.invoke({"user_context": user_context})
        
        # WebSearch 도구 사용 (실제 구현 시)
        # 여기서는 시뮬레이션
        search_query = query_response.content.split("\n")[0] if query_response.content else user_context
        
        # 검색 결과 시뮬레이션 (실제로는 WebSearch 사용)
        search_results = {
            "query": search_query,
            "results": [
                {
                    "title": "청년 마음건강 지원 프로그램",
                    "url": "https://example.com/mental-health",
                    "snippet": "청년들을 위한 무료 심리상담 서비스..."
                }
            ]
        }
        
        # 정보 요약
        summary = f"'{search_query}'에 대한 정보:\n\n{query_response.content}"
        
        return {
            "type": "information",
            "title": "유용한 정보",
            "content": summary,
            "search_query": search_query,
            "sources": search_results.get("results", [])
        }
    
    def generate_experience(self, user_context: str) -> Dict[str, Any]:
        """리츄얼 생성"""
        
        chain = self.exp_prompt | self.llm
        response = chain.invoke({"user_context": user_context})
        
        return {
            "type": "experience",
            "title": "오늘의 리츄얼",
            "content": response.content
        }
    
    def generate_support(
        self,
        user_context: str,
        previous_policy_ids: List[str] = None
    ) -> Dict[str, Any]:
        """정책 추천"""
        
        policy = self.search_relevant_policy(user_context, previous_policy_ids)
        
        if not policy:
            return {
                "type": "support",
                "title": "추천 정책 없음",
                "content": "현재 모든 관련 정책을 확인하셨습니다.",
                "policy_id": None
            }
        
        # 간단한 소개
        intro = f"{policy['policy_name']}\n\n{policy['support_content'][:200]}...\n\n신청: {policy['application_url']}"
        
        return {
            "type": "support",
            "title": policy["policy_name"],
            "content": intro,
            "policy_id": policy["policy_id"],
            "application_url": policy["application_url"],
            "organization": policy["organization"]
        }
    
    def generate_all_contents(
        self,
        user_context: str,
        previous_policy_ids: List[str] = None
    ) -> GrowthContent:
        """3종 콘텐츠 병렬 생성"""
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            info_future = executor.submit(self.generate_information, user_context)
            exp_future = executor.submit(self.generate_experience, user_context)
            support_future = executor.submit(self.generate_support, user_context, previous_policy_ids)
            
            information = info_future.result()
            experience = exp_future.result()
            support = support_future.result()
        
        return GrowthContent(
            information=information,
            experience=experience,
            support=support
        )
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        user_context = state.get("user_context", "")
        previous_policy_ids = state.get("previous_policy_ids", [])
        
        # 3종 콘텐츠 생성
        growth_content = self.generate_all_contents(user_context, previous_policy_ids)
        
        # 상태 업데이트
        state["growth_content"] = {
            "information": growth_content.information,
            "experience": growth_content.experience,
            "support": growth_content.support
        }
        state["growth_completed"] = True
        
        # 정책 ID 추가
        if growth_content.support.get("policy_id"):
            if "viewed_policy_ids" not in state:
                state["viewed_policy_ids"] = []
            state["viewed_policy_ids"].append(growth_content.support["policy_id"])
        
        return state
    
    def close(self):
        """연결 종료"""
        connections.disconnect("default")