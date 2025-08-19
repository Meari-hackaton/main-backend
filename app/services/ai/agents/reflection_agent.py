from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os


class ReflectionCard(BaseModel):
    """성찰 카드 응답"""
    content: str = Field(description="성찰 카드 내용")
    problem: str = Field(description="핵심 문제")
    contexts: List[str] = Field(description="맥락적 요인들")
    affected_groups: List[str] = Field(description="영향받는 집단들")
    initiatives: List[str] = Field(description="해결 시도들")
    stakeholders: List[str] = Field(description="관련 기관들")
    insight: str = Field(description="핵심 통찰")


class ReflectionAgent:
    """Graph RAG 기반 성찰 카드 생성 에이전트"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.6,  # 균형잡힌 온도
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.prompt = self._create_prompt()
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """성찰 카드 생성 프롬프트"""
        
        system_message = """당신은 청년들의 문제를 사회적 맥락에서 이해하는 상담사입니다.
그래프 데이터를 바탕으로 "당신은 혼자가 아니에요"라는 메시지를 전달하는 성찰 카드를 작성하세요.

## 작성 원칙:
1. 개인의 문제가 아닌 사회적 현상임을 강조
2. 같은 어려움을 겪는 집단이 있음을 보여줌
3. 사회가 이미 해결을 위해 노력하고 있음을 전달
4. 비판이나 평가 없이 구조적 이해 제공
5. 희망적이지만 현실적인 톤 유지

## 구성 요소:
- 문제 인식: 당신이 겪는 [문제]는...
- 맥락적 이해: [원인들]로 인한 사회적 현상
- 공감대 형성: [집단들]도 같은 어려움 경험
- 사회적 노력: [기관들]의 [해결 시도들]
- 통찰: 구조적 문제임을 인정하고 연대 강조

## 피해야 할 표현:
- "개인의 노력으로 극복하세요"
- "긍정적으로 생각하세요"
- 문제를 축소하거나 단순화하는 표현"""
        
        human_template = """다음 그래프 분석 결과를 바탕으로 성찰 카드를 작성하세요:

문제: {problem}
맥락적 요인들: {contexts}
영향받는 집단들: {affected_groups}
해결 시도들: {initiatives}
관련 기관들: {stakeholders}

사용자 상황: {user_context}

성찰 카드:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def analyze_graph_results(self, graph_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """그래프 결과 분석 및 정리"""
        
        # 결과 집계
        problems = []
        contexts = []
        affected_groups = []
        initiatives = []
        stakeholders = []
        
        for result in graph_results:
            # 각 필드별로 수집
            if "problem" in result:
                problems.append(result["problem"])
            
            if "cause" in result or "context" in result:
                contexts.append(result.get("cause") or result.get("context"))
            
            if "affected_group" in result or "cohort" in result:
                affected_groups.append(result.get("affected_group") or result.get("cohort"))
            
            if "initiative" in result or "solution" in result:
                initiatives.append(result.get("initiative") or result.get("solution"))
            
            if "stakeholder" in result or "organization" in result:
                stakeholders.append(result.get("stakeholder") or result.get("organization"))
            
            # 리스트 형태로 온 경우 처리
            if "contexts" in result and isinstance(result["contexts"], list):
                contexts.extend(result["contexts"])
            if "affected_groups" in result and isinstance(result["affected_groups"], list):
                affected_groups.extend(result["affected_groups"])
            if "initiatives" in result and isinstance(result["initiatives"], list):
                initiatives.extend(result["initiatives"])
            if "stakeholders" in result and isinstance(result["stakeholders"], list):
                stakeholders.extend(result["stakeholders"])
        
        # 중복 제거 및 정리
        return {
            "problem": problems[0] if problems else "알 수 없는 문제",
            "contexts": list(set(filter(None, contexts)))[:5],  # 최대 5개
            "affected_groups": list(set(filter(None, affected_groups)))[:5],
            "initiatives": list(set(filter(None, initiatives)))[:5],
            "stakeholders": list(set(filter(None, stakeholders)))[:5]
        }
    
    def generate_reflection_card(
        self,
        graph_data: Dict[str, Any],
        user_context: str
    ) -> ReflectionCard:
        """성찰 카드 생성"""
        
        # 프롬프트에 데이터 전달
        chain = self.prompt | self.llm
        response = chain.invoke({
            "problem": graph_data["problem"],
            "contexts": ", ".join(graph_data["contexts"]) if graph_data["contexts"] else "알 수 없음",
            "affected_groups": ", ".join(graph_data["affected_groups"]) if graph_data["affected_groups"] else "많은 청년들",
            "initiatives": ", ".join(graph_data["initiatives"]) if graph_data["initiatives"] else "다양한 정책",
            "stakeholders": ", ".join(graph_data["stakeholders"]) if graph_data["stakeholders"] else "여러 기관",
            "user_context": user_context
        })
        
        # 통찰 생성
        insight = self._generate_insight(graph_data)
        
        return ReflectionCard(
            content=response.content,
            problem=graph_data["problem"],
            contexts=graph_data["contexts"],
            affected_groups=graph_data["affected_groups"],
            initiatives=graph_data["initiatives"],
            stakeholders=graph_data["stakeholders"],
            insight=insight
        )
    
    def _generate_insight(self, graph_data: Dict[str, Any]) -> str:
        """핵심 통찰 생성"""
        
        # 데이터 기반 통찰
        if len(graph_data["contexts"]) > 2:
            return f"이 문제는 {len(graph_data['contexts'])}개 이상의 복합적 요인이 작용하는 구조적 문제입니다."
        elif len(graph_data["stakeholders"]) > 2:
            return f"{len(graph_data['stakeholders'])}개 이상의 기관이 함께 해결하려 노력하는 사회적 과제입니다."
        elif graph_data["affected_groups"]:
            return f"당신뿐만 아니라 {', '.join(graph_data['affected_groups'][:2])} 등 많은 이들이 겪는 공통의 어려움입니다."
        else:
            return "이 문제는 개인의 잘못이 아닌 우리 사회가 함께 해결해야 할 과제입니다."
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        # CypherAgent 결과 가져오기
        graph_results = state.get("graph_results", [])
        user_context = state.get("user_context", "")
        
        # 그래프 결과 분석
        graph_data = self.analyze_graph_results(graph_results)
        
        # 성찰 카드 생성
        reflection_card = self.generate_reflection_card(graph_data, user_context)
        
        # 상태 업데이트
        state["reflection_card"] = {
            "content": reflection_card.content,
            "problem": reflection_card.problem,
            "contexts": reflection_card.contexts,
            "affected_groups": reflection_card.affected_groups,
            "initiatives": reflection_card.initiatives,
            "stakeholders": reflection_card.stakeholders,
            "insight": reflection_card.insight
        }
        state["reflection_completed"] = True
        
        return state