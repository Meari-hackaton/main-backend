from typing import Dict, Any, List, Literal, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os


class RoutingDecision(BaseModel):
    """라우팅 결정"""
    request_type: Literal["initial_session", "growth_content", "ritual"] = Field(
        description="요청 타입"
    )
    required_agents: List[str] = Field(
        description="필요한 에이전트 목록"
    )
    parallel_execution: bool = Field(
        default=True,
        description="병렬 실행 가능 여부"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="에이전트에 전달할 컨텍스트"
    )


class SupervisorAgent:
    """요청을 적절한 에이전트로 라우팅하는 감독 에이전트"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.1,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.routing_prompt = self._create_routing_prompt()
    
    def _create_routing_prompt(self) -> ChatPromptTemplate:
        """라우팅 프롬프트 생성"""
        
        system_message = """당신은 메아리 서비스의 라우팅 감독자입니다.
요청을 분석하여 적절한 에이전트로 작업을 분배하세요.

## 요청 타입별 라우팅 규칙:

### 1. initial_session (첫 분석)
- 필요 에이전트: ["empathy", "cypher", "reflection", "persona"]
- 병렬 실행: empathy와 cypher는 병렬 가능
- 순서: empathy/cypher(병렬) → reflection → persona

### 2. growth_content (성장 콘텐츠)
- 필요 에이전트: ["growth"]
- 병렬 실행: growth 내부에서 3종 병렬 생성

### 3. ritual (리츄얼 기록)
- 필요 에이전트: ["persona"]
- 병렬 실행: 불필요
- 페르소나 업데이트만 수행

## 컨텍스트 추출:
- tag_ids: 선택된 태그 ID 목록
- user_context: 사용자 입력 텍스트
- previous_policy_ids: 이미 본 정책 ID 목록
- ritual_data: 리츄얼 일기 데이터

반드시 JSON 형태로 응답하세요."""
        
        human_template = """다음 요청을 분석하여 라우팅하세요:

요청 데이터: {request_data}

JSON 응답:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def route_request(self, request_data: Dict[str, Any]) -> RoutingDecision:
        """요청을 분석하여 라우팅 결정"""
        
        # API 엔드포인트로 요청 타입 판단
        endpoint = request_data.get("endpoint", "")
        
        if "meari-sessions" in endpoint or request_data.get("type") == "initial":
            return RoutingDecision(
                request_type="initial_session",
                required_agents=["empathy", "cypher", "reflection", "persona"],
                parallel_execution=True,
                context={
                    "tag_ids": request_data.get("tag_ids", []),
                    "user_context": request_data.get("user_context", "")
                }
            )
        
        elif "growth-contents" in endpoint or request_data.get("type") == "growth":
            return RoutingDecision(
                request_type="growth_content",
                required_agents=["growth"],
                parallel_execution=False,
                context={
                    "context_type": request_data.get("context", "initial"),
                    "previous_policy_ids": request_data.get("previous_policy_ids", []),
                    "persona": request_data.get("persona", {})
                }
            )
        
        elif "rituals" in endpoint or request_data.get("type") == "ritual":
            return RoutingDecision(
                request_type="ritual",
                required_agents=["persona"],
                parallel_execution=False,
                context={
                    "diary_entry": request_data.get("diary_entry", ""),
                    "selected_mood": request_data.get("selected_mood", ""),
                    "growth_contents_viewed": request_data.get("growth_contents_viewed", [])
                }
            )
        
        else:
            # LLM으로 판단
            chain = self.routing_prompt | self.llm
            response = chain.invoke({"request_data": request_data})
            
            # 응답 파싱
            import json
            try:
                result = json.loads(response.content)
                return RoutingDecision(**result)
            except:
                # 기본값 반환
                return RoutingDecision(
                    request_type="initial_session",
                    required_agents=["empathy"],
                    parallel_execution=False,
                    context={}
                )
    
    def coordinate_agents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 실행 조정"""
        
        # 라우팅 결정
        routing = self.route_request(state.get("request_data", {}))
        
        # 상태에 라우팅 정보 추가
        state["routing"] = {
            "type": routing.request_type,
            "agents": routing.required_agents,
            "parallel": routing.parallel_execution,
            "context": routing.context
        }
        
        # 실행 순서 결정
        if routing.request_type == "initial_session":
            # 공감과 Cypher는 병렬, 성찰은 이후, 페르소나는 마지막
            state["execution_plan"] = [
                ["empathy", "cypher"],  # 병렬
                ["reflection"],  # Cypher 결과 필요
                ["persona"]  # 모든 결과 필요
            ]
        
        elif routing.request_type == "growth_content":
            state["execution_plan"] = [["growth"]]
        
        elif routing.request_type == "ritual":
            state["execution_plan"] = [["persona"]]
        
        return state
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        # 요청 데이터 추출
        request_data = {
            "endpoint": state.get("endpoint", ""),
            "type": state.get("request_type", ""),
            "tag_ids": state.get("tag_ids", []),
            "user_context": state.get("user_context", ""),
            "context": state.get("context", "initial"),
            "previous_policy_ids": state.get("previous_policy_ids", []),
            "diary_entry": state.get("diary_entry", ""),
            "selected_mood": state.get("selected_mood", ""),
            "growth_contents_viewed": state.get("growth_contents_viewed", [])
        }
        
        state["request_data"] = request_data
        
        # 에이전트 조정
        state = self.coordinate_agents(state)
        
        return state
    
    def should_continue(self, state: Dict[str, Any]) -> str:
        """다음 노드 결정"""
        
        routing_type = state.get("routing", {}).get("type", "")
        
        if routing_type == "initial_session":
            # 실행 계획에 따라 다음 에이전트 결정
            if not state.get("empathy_completed"):
                return "empathy"
            elif not state.get("cypher_completed"):
                return "cypher"
            elif not state.get("reflection_completed"):
                return "reflection"
            elif not state.get("persona_completed"):
                return "persona"
            else:
                return "synthesizer"
        
        elif routing_type == "growth_content":
            if not state.get("growth_completed"):
                return "growth"
            else:
                return "synthesizer"
        
        elif routing_type == "ritual":
            if not state.get("persona_completed"):
                return "persona"
            else:
                return "synthesizer"
        
        return "end"