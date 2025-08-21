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
        
        system_message = """당신은 한국 청년(19-34세)의 고민을 이해하고 실질적인 도움을 주는 전문 상담사입니다.
청년들의 취업 스트레스, 직장 내 번아웃, 우울감, 사회적 고립감, 관계 스트레스 등에 대한 실용적인 정보를 제공하세요.

## 응답 형식 (JSON):
{{
    "title": "취업 스트레스 관리법",  
    "content": "취업 준비 과정에서 느끼는 스트레스는 자연스러운 반응입니다. 중요한 것은 이를 건강하게 관리하는 방법입니다. 첫째, 매일 달성 가능한 작은 목표를 설정하세요. '오늘은 자소서 한 문단 완성'처럼 구체적이고 실현 가능한 목표가 좋습니다. 둘째, 규칙적인 운동과 충분한 수면을 유지하세요. 신체 건강이 정신 건강의 기반입니다. 셋째, 같은 상황의 동료들과 소통하며 정보와 감정을 공유하세요. 혼자가 아님을 아는 것만으로도 큰 힘이 됩니다.",
    "summary": "취업 스트레스를 건강하게 관리하는 실천 방법",
    "search_query": "청년 취업 스트레스 극복",
    "key_points": ["작은 목표 설정하기", "규칙적인 생활 습관", "동료와의 소통"]
}}

## 주제 예시:
- 취업/이직 준비, 서류 작성법, 면접 대비
- 직장 내 스트레스 관리, 번아웃 예방
- 우울감 극복, 불안 관리, 수면 개선
- 대인관계 개선, 사회적 연결감 회복
- 경제적 자립, 주거 문제 해결

## 작성 원칙:
1. 한국 청년이 실제로 겪는 문제에 대한 실질적 조언
2. 바로 실천 가능한 구체적인 방법 제시
3. 관련 정책이나 지원 서비스 정보 포함
4. 희망적이면서도 현실적인 톤
5. 200-300자 내외의 명확한 설명
6. 절대 '페르소나', '캐릭터', 'RPG', '게임' 등의 개념 사용 금지"""
        
        human_template = """사용자 상황: {user_context}

위 상황에 실질적으로 도움이 될 정보를 JSON 형식으로 제공하세요:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def _create_exp_prompt(self) -> ChatPromptTemplate:
        """경험 리츄얼 생성 프롬프트"""
        
        system_message = """당신은 한국 청년의 심리 회복을 돕는 전문 상담사입니다.
청년의 취업 스트레스, 번아웃, 우울감, 관계 고민 등에 도움이 되는 실천 가능한 리츄얼을 제안하세요.

## 응답 형식 (JSON):
{{
    "ritual_name": "감사 일기 쓰기",
    "description": "오늘 하루 감사한 3가지를 기록하며 긍정적인 마음을 회복하는 시간",
    "steps": ["조용한 공간에서 노트나 메모앱 준비", "오늘 있었던 작은 감사한 일 3가지 떠올리기", "각각에 대해 2-3문장으로 구체적으로 기록", "작성한 내용을 천천히 다시 읽으며 마음에 새기기"],
    "duration": "10분",
    "immediate_effect": "부정적 사고의 전환, 마음의 안정",
    "long_term_effect": "긍정적 사고 습관 형성, 정서적 회복력 향상"
}}

## 리츄얼 예시:
- 호흡 명상, 감사 일기, 짧은 산책
- 스트레칭, 좋아하는 음악 듣기
- 친구에게 안부 메시지 보내기
- 작은 목표 설정하고 달성하기

## 원칙:
1. 10분 이내로 실천 가능
2. 특별한 도구나 장소 불필요  
3. 청년의 실제 고민 해결에 도움
4. 구체적이고 따라하기 쉬운 단계
5. 절대 '페르소나', '캐릭터', 'RPG' 등의 개념 사용 금지"""
        
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
                # 상황별 적절한 URL 매핑
                url_map = {
                    "취업": "https://www.work.go.kr/seekWantedMain.do",
                    "번아웃": "https://www.blutouch.net",
                    "우울": "https://www.ncmh.go.kr",
                    "정책": "https://www.youthcenter.go.kr",
                    "상담": "https://www.129.go.kr",
                    "건강": "https://www.mohw.go.kr"
                }
                
                # 키워드 기반 URL 선택
                default_url = "https://www.youthcenter.go.kr"
                selected_url = default_url
                for keyword, url in url_map.items():
                    if keyword in user_context or keyword in result.get("title", ""):
                        selected_url = url
                        break
                
                return {
                    "type": "information",
                    "title": result.get("title", "맞춤형 정보"),
                    "content": result.get("content", ""),
                    "summary": result.get("summary", ""),
                    "search_query": result.get("search_query", user_context),
                    "sources": [
                        {
                            "title": "관련 정보 더보기",
                            "url": selected_url,
                            "snippet": result.get("summary", "자세한 정보를 확인하세요")
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
        """3종 콘텐츠 한번의 LLM 호출로 생성"""
        
        # 정책은 벡터 검색으로
        support = self.generate_support(user_context, previous_policy_ids)
        
        # 정보와 경험은 하나의 프롬프트로 통합 생성
        combined_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 한국 청년의 고민을 이해하고 도움을 주는 상담사입니다.
사용자 상황에 맞는 정보와 리츄얼을 JSON으로 제공하세요.

응답 형식:
{{
    "information": {{
        "title": "제목",
        "content": "실용적인 정보 (200-300자)",
        "summary": "한줄 요약",
        "search_query": "검색 쿼리"
    }},
    "experience": {{
        "ritual_name": "리츄얼 이름",
        "description": "설명 (50-100자)",
        "steps": ["단계1", "단계2", "단계3"],
        "duration": "5-10분",
        "immediate_effect": "즉각 효과",
        "long_term_effect": "장기 효과"
    }}
}}"""),
            ("human", "사용자 상황: {user_context}\n\n위 상황에 맞는 정보와 리츄얼을 JSON으로 작성하세요:")
        ])
        
        try:
            chain = combined_prompt | self.llm
            response = chain.invoke({"user_context": user_context})
            
            import json
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            
            # URL 매핑
            url_map = {
                "취업": "https://www.work.go.kr/seekWantedMain.do",
                "번아웃": "https://www.blutouch.net",
                "우울": "https://www.ncmh.go.kr",
                "정책": "https://www.youthcenter.go.kr",
                "상담": "https://www.129.go.kr",
                "건강": "https://www.mohw.go.kr"
            }
            
            selected_url = "https://www.youthcenter.go.kr"
            for keyword, url in url_map.items():
                if keyword in user_context or keyword in result.get("information", {}).get("title", ""):
                    selected_url = url
                    break
            
            information = {
                "type": "information",
                "title": result["information"]["title"],
                "content": result["information"]["content"],
                "summary": result["information"]["summary"],
                "search_query": result["information"]["search_query"],
                "sources": [{
                    "title": "관련 정보 더보기",
                    "url": selected_url,
                    "snippet": result["information"]["summary"]
                }]
            }
            
            experience = {
                "type": "experience",
                "title": "오늘의 리츄얼",
                "ritual_name": result["experience"]["ritual_name"],
                "description": result["experience"]["description"],
                "steps": result["experience"]["steps"],
                "duration": result["experience"]["duration"],
                "immediate_effect": result["experience"]["immediate_effect"],
                "long_term_effect": result["experience"]["long_term_effect"]
            }
            
        except Exception as e:
            print(f"통합 생성 실패, 개별 생성으로 폴백: {e}")
            # 폴백: 병렬 실행
            with ThreadPoolExecutor(max_workers=2) as executor:
                info_future = executor.submit(self.generate_information, user_context)
                exp_future = executor.submit(self.generate_experience, user_context)
                
                information = info_future.result()
                experience = exp_future.result()
        
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