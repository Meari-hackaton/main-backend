from typing import TypedDict, Dict, Any, List, Optional, Literal, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator
from functools import partial

from app.services.ai.agents.supervisor_agent import SupervisorAgent
from app.services.ai.agents.cypher_agent import CypherAgent
from app.services.ai.agents.empathy_agent import EmpathyAgent
from app.services.ai.agents.reflection_agent import ReflectionAgent
from app.services.ai.agents.growth_agent import GrowthAgent
from app.services.ai.agents.persona_agent import PersonaAgent
from app.services.ai.agents.card_synthesizer_agent import CardSynthesizerAgent
from app.services.ai.config import AIConfig
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor


class MeariState(TypedDict):
    """메아리 워크플로우 상태"""
    
    # 입력 데이터
    request_type: Literal["initial_session", "growth_content", "ritual"]
    endpoint: str
    user_context: str
    tag_ids: List[int]
    context_type: str  # growth_content용 (initial/ritual)
    persona_summary: str  # growth_content용
    previous_policy_ids: List[str]
    previous_rituals: List[str]
    diary_entry: str
    selected_mood: str
    growth_contents_viewed: List[str]
    
    # 라우팅 정보
    routing: Dict[str, Any]
    execution_plan: List[List[str]]
    
    # 에이전트 결과
    empathy_card: Dict[str, Any]
    reflection_card: Dict[str, Any]
    growth_content: Dict[str, Any]
    persona: Dict[str, Any]
    
    # Graph RAG 데이터
    reflection_query: str
    cypher_query: str
    graph_results: List[Dict[str, Any]]
    
    # 완료 플래그
    empathy_completed: bool
    cypher_completed: bool
    reflection_completed: bool
    growth_completed: bool
    persona_completed: bool
    
    # 최종 응답
    final_response: Dict[str, Any]
    
    # 에러 추적
    errors: Annotated[Sequence[str], operator.add]


class MeariWorkflow:
    """메아리 LangGraph 워크플로우"""
    
    def __init__(self):
        # API 키 로드밸런싱을 위한 설정
        api_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY2"),
            os.getenv("GEMINI_API_KEY3")
        ]
        valid_keys = [k for k in api_keys if k]
        
        # 각 에이전트에 다른 API 키 할당
        self.supervisor = SupervisorAgent()
        self.cypher = CypherAgent()
        self.empathy = EmpathyAgent(api_key=valid_keys[0] if len(valid_keys) > 0 else None)
        self.reflection = ReflectionAgent()
        self.growth = GrowthAgent()
        self.persona = PersonaAgent()
        self.synthesizer = CardSynthesizerAgent()
        
        # 워크플로우 구성
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """워크플로우 그래프 구성"""
        
        workflow = StateGraph(MeariState)
        
        # 노드 추가
        workflow.add_node("supervisor", self.supervisor.process)
        workflow.add_node("cypher", self.cypher.process)
        workflow.add_node("empathy", self.empathy.process)
        workflow.add_node("reflection", self.reflection.process)
        workflow.add_node("growth", self.growth.process)
        workflow.add_node("persona", self.persona.process)
        workflow.add_node("synthesizer", self.synthesizer.process)
        
        # 시작점 설정
        workflow.set_entry_point("supervisor")
        
        # 라우팅 로직
        workflow.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {
                "parallel_empathy_cypher": "parallel_empathy_cypher",
                "growth": "growth",
                "persona_update": "persona",
                "end": END
            }
        )
        
        # Initial Session 병렬 처리 플로우
        workflow.add_node("parallel_empathy_cypher", self._parallel_empathy_cypher)
        workflow.add_edge("parallel_empathy_cypher", "reflection")
        
        workflow.add_edge("reflection", "persona")
        
        # Growth Content 플로우
        workflow.add_edge("growth", "synthesizer")
        
        # Persona 플로우
        workflow.add_conditional_edges(
            "persona",
            self._route_after_persona,
            {
                "synthesizer": "synthesizer",
                "growth": "growth"
            }
        )
        
        # 최종 합성
        workflow.add_edge("synthesizer", END)
        
        return workflow
    
    def _route_after_supervisor(self, state: MeariState) -> str:
        """Supervisor 후 라우팅"""
        
        routing_type = state.get("routing", {}).get("type", "")
        
        if routing_type == "initial_session":
            return "parallel_empathy_cypher"  # 병렬 실행
        elif routing_type == "growth_content":
            return "growth"
        elif routing_type == "ritual":
            return "persona_update"
        else:
            return "end"
    
    def _route_after_persona(self, state: MeariState) -> str:
        """Persona 후 라우팅"""
        
        routing_type = state.get("routing", {}).get("type", "")
        
        if routing_type == "initial_session":
            return "growth"  # Initial session 후 growth content도 생성
        else:
            return "synthesizer"
    
    def _parallel_empathy_cypher(self, state: MeariState) -> MeariState:
        """Empathy와 Cypher를 병렬로 실행"""
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 병렬 실행
            empathy_future = executor.submit(self.empathy.process, state.copy())
            cypher_future = executor.submit(self.cypher.process, state.copy())
            
            # 결과 수집
            empathy_result = empathy_future.result()
            cypher_result = cypher_future.result()
            
            # 디버깅: Empathy 결과 확인
            print(f"\n=== EmpathyAgent 결과 ===")
            print(f"empathy_card 키 존재: {'empathy_card' in empathy_result}")
            if 'empathy_card' in empathy_result:
                print(f"empathy_card content: {empathy_result['empathy_card'].get('content', '')[:100]}...")
                print(f"empathy_card cards 개수: {len(empathy_result['empathy_card'].get('cards', []))}")
            
            # 상태 병합 - 각 에이전트의 모든 업데이트를 병합
            # Empathy 에이전트의 업데이트 병합
            for key, value in empathy_result.items():
                if value is not None:
                    state[key] = value
            
            # Cypher 에이전트의 업데이트 병합
            for key, value in cypher_result.items():
                if value is not None and key != 'empathy_card':  # empathy_card는 덮어쓰지 않음
                    state[key] = value
            
            # 완료 플래그 설정
            state["empathy_completed"] = True
            state["cypher_completed"] = True
            
            # 디버깅: 병합 후 상태 확인
            print(f"\n=== 병렬 실행 후 상태 병합 ===")
            print(f"graph_results 개수: {len(state.get('graph_results', []))}")
            if state.get('graph_results'):
                print(f"첫 번째 graph_result: {state['graph_results'][0]}")
            
        return state
    
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """요청 처리"""
        
        # 초기 상태 생성
        initial_state = MeariState(
            request_type=request_data.get("request_type", "initial_session"),
            endpoint=request_data.get("endpoint", ""),
            user_context=request_data.get("user_context", ""),
            tag_ids=request_data.get("tag_ids", []),
            context_type=request_data.get("context", "initial"),  # growth_content용
            persona_summary=request_data.get("persona_summary", ""),  # growth_content용
            previous_policy_ids=request_data.get("previous_policy_ids", []),
            previous_rituals=request_data.get("previous_rituals", []),
            diary_entry=request_data.get("diary_entry", ""),
            selected_mood=request_data.get("selected_mood", ""),
            growth_contents_viewed=request_data.get("growth_contents_viewed", []),
            routing={},
            execution_plan=[],
            empathy_card={},
            reflection_card={},
            growth_content={},
            persona={},
            reflection_query="",
            cypher_query="",
            graph_results=[],
            empathy_completed=False,
            cypher_completed=False,
            reflection_completed=False,
            growth_completed=False,
            persona_completed=False,
            final_response={},
            errors=[]
        )
        
        try:
            # 워크플로우 실행
            result = self.app.invoke(initial_state)
            return result.get("final_response", {})
        except Exception as e:
            return {
                "error": str(e),
                "message": "워크플로우 처리 중 오류가 발생했습니다."
            }
    
    def close(self):
        """리소스 정리"""
        if hasattr(self.cypher, 'close'):
            self.cypher.close()
        if hasattr(self.empathy, 'close'):
            self.empathy.close()
        if hasattr(self.growth, 'close'):
            self.growth.close()