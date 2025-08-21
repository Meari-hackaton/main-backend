from typing import Dict, Any, List, Optional, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from pymilvus import Collection, connections
from app.services.data.vector_store import get_policies_collection
from app.services.data.embedding_service import embed_text
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
        
        # 프롬프트 설정
        self.info_prompt = self._create_info_prompt()
        self.exp_prompt = self._create_exp_prompt()
    
    def _get_collection(self):
        """Milvus 커렉션 가져오기 (lazy loading)"""
        if self.policies_collection is None:
            self.policies_collection = get_policies_collection()
        return self.policies_collection
    
    def _create_info_prompt(self) -> ChatPromptTemplate:
        """정보 콘텐츠 생성 프롬프트"""
        
        system_message = """사용자 상황에 맞는 유용한 정보를 제공하세요.

## 응답 형식 (JSON):
{{
    "title": "구체적인 제목",
    "content": "200-300자의 핵심 정보와 실용적 조언",
    "summary": "한 줄 요약",
    "search_query": "관련 검색어",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]
}}

## 원칙:
1. 실용적이고 구체적인 정보 제공
2. 즉시 활용 가능한 팁 포함
3. 공감적이고 희망적인 톤"""
        
        human_template = """사용자 상황: {user_context}

위 상황에 도움이 될 정보를 JSON 형식으로 제공하세요:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def _create_exp_prompt(self) -> ChatPromptTemplate:
        """경험 리츄얼 생성 프롬프트"""
        
        system_message = """사용자 상황에 맞는 10분 이내 리츄얼을 제안하세요.

## 응답 형식 (JSON):
{{
    "ritual_name": "리츄얼 이름",
    "description": "리츄얼 설명 (50-100자)",
    "steps": ["단계 1", "단계 2", "단계 3"],
    "duration": "소요 시간",
    "immediate_effect": "즉각적 효과",
    "long_term_effect": "장기적 효과"
}}

## 원칙:
1. 10분 이내로 실천 가능
2. 특별한 도구나 장소 불필요
3. 즉각적 효과가 있는 활동
4. 구체적이고 따라하기 쉬운 단계"""
        
        human_template = """사용자 상황: {user_context}

위 상황에 도움이 될 리츄얼을 JSON 형식으로 제안하세요:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def search_policy(
        self, 
        user_context: str,
        previous_policy_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """관련 정책 검색"""
        
        if previous_policy_ids is None:
            previous_policy_ids = []
        
        query_embedding = embed_text(user_context)
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
                "type": "support",
                "title": "맞춤형 지원 정책",
                "policy_id": hit.entity.get("policy_id"),
                "policy_name": hit.entity.get("policy_name"),
                "support_content": hit.entity.get("support_content"),
                "application_url": hit.entity.get("application_url"),
                "organization": hit.entity.get("organization"),
                "eligibility": "만 19-34세 청년",
                "how_to_apply": "온라인 신청"
            }
        
        # 기본 정책 반환
        return {
            "type": "support",
            "title": "맞춤형 지원 정책",
            "policy_id": "default_001",
            "policy_name": "청년 마음건강 바우처 지원",
            "support_content": "정신건강의학과, 심리상담센터 이용 비용 지원 (연 60만원 한도)",
            "application_url": "https://www.youthcenter.go.kr",
            "organization": "여성가족부",
            "eligibility": "만 19-34세 청년",
            "how_to_apply": "온라인 신청"
        }
    
    def generate_information(self, user_context: str) -> Dict[str, Any]:
        """정보 콘텐츠 생성"""
        import json
        
        # LLM에게 정보 생성 요청
        chain = self.info_prompt | self.llm
        response = chain.invoke({"user_context": user_context})
        
        try:
            # JSON 파싱 시도
            if response.content:
                # JSON 부분만 추출
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content)
                
                # 필수 필드 확인 및 기본값 설정
                return {
                    "type": "information",
                    "title": result.get("title", "맞춤형 정보"),
                    "content": result.get("content", ""),
                    "summary": result.get("summary", ""),
                    "search_query": result.get("search_query", user_context),
                    "sources": [
                        {
                            "title": f"{result.get('title', '관련 정보')} - 추천 자료",
                            "url": "https://www.youthcenter.go.kr",
                            "snippet": result.get("key_points", [""])[0] if result.get("key_points") else "청년 지원 정보"
                        }
                    ]
                }
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트 기반 처리
            content = response.content.strip() if response.content else ""
            
        # 폴백: 기본 응답
        return {
            "type": "information",
            "title": "맞춤형 정보",
            "content": content[:300] if len(content) > 300 else content,
            "summary": content[:100] if content else "사용자 맞춤 정보",
            "search_query": user_context,
            "sources": [
                {
                    "title": "청년 지원 센터",
                    "url": "https://www.youthcenter.go.kr",
                    "snippet": "다양한 청년 지원 프로그램 제공"
                }
            ]
        }
    
    def generate_experience(self, user_context: str) -> Dict[str, Any]:
        """경험 리츄얼 제안"""
        import json
        
        # LLM에게 리츄얼 생성 요청
        chain = self.exp_prompt | self.llm
        response = chain.invoke({"user_context": user_context})
        
        try:
            # JSON 파싱 시도
            if response.content:
                # JSON 부분만 추출
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content)
                
                # 필수 필드 확인 및 반환
                return {
                    "type": "experience",
                    "title": "오늘의 리츄얼",
                    "ritual_name": result.get("ritual_name", "마음챙기기 리츄얼"),
                    "description": result.get("description", ""),
                    "steps": result.get("steps", []),
                    "duration": result.get("duration", "5-10분"),
                    "immediate_effect": result.get("immediate_effect", "마음의 안정"),
                    "long_term_effect": result.get("long_term_effect", "정서적 탄력성 향상")
                }
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트 기반 처리
            content = response.content.strip() if response.content else ""
            
        # 폴백: 기본 리츄얼
        return {
            "type": "experience",
            "title": "오늘의 리츄얼",
            "ritual_name": "마음챙기기",
            "description": "잠시 멈추고 현재에 집중하는 시간",
            "steps": [
                "1. 편안한 자세로 앉기",
                "2. 천천히 심호흡 3회",
                "3. 현재 드는 감정 인식하기"
            ],
            "duration": "5-10분",
            "immediate_effect": "마음의 안정",
            "long_term_effect": "정서적 탄력성 향상"
        }
    
    def generate_support(
        self,
        user_context: str,
        previous_policy_ids: List[str] = None
    ) -> Dict[str, Any]:
        """정책 추천"""
        
        policy = self.search_policy(user_context, previous_policy_ids)
        
        if policy:
            return policy
        
        # 기본 정책 추가
        return {
            "type": "support",
            "title": "맞춤형 지원 정책",
            "policy_id": "default_001",
            "policy_name": "청년 마음건강 지원 사업",
            "support_content": "심리상담 비용 지원",
            "application_url": "https://www.youthcenter.go.kr",
            "organization": "여성가족부",
            "eligibility": "만 19-34세 청년",
            "how_to_apply": "온라인 신청"
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
        
        # persona_summary 또는 user_context 사용
        user_context = state.get("persona_summary") or state.get("user_context", "")
        previous_policy_ids = state.get("previous_policy_ids", [])
        
        # 3종 콘텐츠 생성
        growth_content = self.generate_all_contents(user_context, previous_policy_ids)
        
        # 상태 업데이트 - growth_content로 저장 (card_synthesizer가 이를 cards로 변환)
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