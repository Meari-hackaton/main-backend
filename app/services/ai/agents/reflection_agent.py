from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os


class InsightCard(BaseModel):
    """개별 인사이트 카드"""
    title: str = Field(description="카드 제목")
    content: str = Field(description="카드 내용 (200-300자)")
    news_id: Optional[str] = Field(description="관련 뉴스 ID")
    news_title: Optional[str] = Field(description="관련 뉴스 제목")
    news_date: Optional[str] = Field(description="관련 뉴스 날짜")
    key_points: List[str] = Field(description="핵심 포인트 3개")
    
class ReflectionCards(BaseModel):
    """성찰 카드 3종 세트"""
    cards: List[InsightCard] = Field(description="3개의 인사이트 카드")


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
주어진 데이터 각각에 대해 독립적인 인사이트 카드를 작성하세요.

## 작성 원칙:
1. 각 카드는 200-300자로 작성
2. 카드별로 다른 관점 제시
3. 구체적인 통계나 사실 포함
4. 희망적이지만 현실적인 톤

## 카드 유형:
1. "뉴스가 말해주는 진짜 이유" - 문제의 구조적 원인
2. "왜 이런 일이 생기는 걸까요?" - 사회적 맥락과 배경
3. "희망적인 변화들도 있어요" - 해결 노력과 지원

## 각 카드 구성:
- 제목: 15-20자
- 내용: 200-300자
- 핵심 포인트: 3개 (각 20자 내외)"""
        
        human_template = """다음 3개의 그래프 분석 결과로 각각 다른 인사이트 카드를 작성하세요:

{graph_results}

사용자 상황: {user_context}

3개의 인사이트 카드를 JSON 형식으로 작성:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def generate_reflection_cards(
        self,
        graph_results: List[Dict[str, Any]],
        user_context: str
    ) -> List[InsightCard]:
        """3개의 인사이트 카드 생성"""
        
        # 결과가 없으면 기본 카드 생성
        if not graph_results:
            return self._generate_default_cards()
        
        # 그래프 결과를 JSON 형식으로 변환
        formatted_results = []
        for i, result in enumerate(graph_results[:3], 1):
            formatted_results.append({
                "index": i,
                "news_id": result.get("news_id", ""),
                "news_title": result.get("news_title", ""),
                "news_date": result.get("news_date", ""),
                "problem": result.get("problem", ""),
                "contexts": result.get("contexts", [])[:3],
                "initiatives": result.get("initiatives", [])[:3],
                "stakeholders": result.get("stakeholders", [])[:2],
                "affected_groups": result.get("affected_groups", [])[:2]
            })
        
        # LLM으로 카드 생성
        chain = self.prompt | self.llm
        response = chain.invoke({
            "graph_results": str(formatted_results),
            "user_context": user_context
        })
        
        # 응답 파싱하여 카드 생성
        try:
            import json
            cards_data = json.loads(response.content)
            
            cards = []
            card_titles = [
                "뉴스가 말해주는 진짜 이유",
                "왜 이런 일이 생기는 걸까요?", 
                "희망적인 변화들도 있어요"
            ]
            
            for i, (result, title) in enumerate(zip(graph_results[:3], card_titles)):
                card_data = cards_data[i] if i < len(cards_data) else {}
                
                card = InsightCard(
                    title=card_data.get("title", title),
                    content=card_data.get("content", f"{result.get('problem', '문제')}에 대한 분석"),
                    news_id=result.get("news_id"),
                    news_title=result.get("news_title"),
                    news_date=result.get("news_date"),
                    key_points=card_data.get("key_points", [
                        f"{result.get('contexts', [''])[0]}" if result.get('contexts') else "사회적 요인",
                        f"{result.get('initiatives', [''])[0]}" if result.get('initiatives') else "해결 노력",
                        f"{result.get('affected_groups', [''])[0]}" if result.get('affected_groups') else "함께하는 사람들"
                    ])[:3]
                )
                cards.append(card)
                
            return cards
            
        except Exception as e:
            print(f"카드 파싱 실패: {e}")
            return self._generate_fallback_cards(graph_results)
    
    def _generate_default_cards(self) -> List[InsightCard]:
        """기본 카드 생성"""
        return [
            InsightCard(
                title="뉴스가 말해주는 진짜 이유",
                content="개인의 문제가 아닌 사회 구조적 문제입니다. 많은 청년들이 비슷한 어려움을 겪고 있으며, 이는 우리 사회가 함께 해결해야 할 과제입니다.",
                news_id=None,
                news_title=None,
                news_date=None,
                key_points=["사회 구조적 문제", "많은 청년들의 공통 경험", "함께 해결할 과제"]
            ),
            InsightCard(
                title="왜 이런 일이 생기는 걸까요?",
                content="경쟁 사회, 불안정한 고용 환경, 높은 생활비 등 복합적인 요인이 작용하고 있습니다. 이러한 환경은 개인이 아무리 노력해도 쉽게 바꿀 수 없는 구조적 문제입니다.",
                news_id=None,
                news_title=None,
                news_date=None,
                key_points=["복합적 사회 요인", "구조적 환경 문제", "개인 노력의 한계"]
            ),
            InsightCard(
                title="희망적인 변화들도 있어요",
                content="정부와 여러 기관에서 청년 지원 정책을 확대하고 있습니다. 또한 청년들 스스로도 연대하며 변화를 만들어가고 있습니다. 혼자가 아닌 함께 해결해 나갈 수 있습니다.",
                news_id=None,
                news_title=None,
                news_date=None,
                key_points=["청년 지원 정책 확대", "청년 연대와 변화", "함께하는 해결"]
            )
        ]
    
    def _generate_fallback_cards(self, graph_results: List[Dict[str, Any]]) -> List[InsightCard]:
        """폴백 카드 생성"""
        cards = []
        card_configs = [
            ("뉴스가 말해주는 진짜 이유", "문제의 구조적 원인을 보여줍니다"),
            ("왜 이런 일이 생기는 걸까요?", "사회적 맥락과 배경을 설명합니다"),
            ("희망적인 변화들도 있어요", "해결 노력과 지원을 소개합니다")
        ]
        
        for i, (title, default_content) in enumerate(card_configs):
            if i < len(graph_results):
                result = graph_results[i]
                content = f"{result.get('problem', '청년 문제')}는 "
                if result.get('contexts'):
                    content += f"{', '.join(result['contexts'][:2])} 등의 요인으로 발생합니다. "
                if result.get('initiatives'):
                    content += f"{', '.join(result['initiatives'][:2])} 등의 노력이 진행 중입니다."
                
                cards.append(InsightCard(
                    title=title,
                    content=content[:300],
                    news_id=result.get("news_id"),
                    news_title=result.get("news_title"),
                    news_date=result.get("news_date"),
                    key_points=[
                        result.get('contexts', [''])[0] if result.get('contexts') else "사회적 요인",
                        result.get('initiatives', [''])[0] if result.get('initiatives') else "해결 노력",
                        result.get('affected_groups', [''])[0] if result.get('affected_groups') else "함께하는 사람들"
                    ][:3]
                ))
            else:
                cards.append(InsightCard(
                    title=title,
                    content=default_content,
                    news_id=None,
                    news_title=None,
                    news_date=None,
                    key_points=["분석 중", "분석 중", "분석 중"]
                ))
        
        return cards
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        # CypherAgent 결과 가져오기
        graph_results = state.get("graph_results", [])
        user_context = state.get("user_context", "")
        
        # 3개의 인사이트 카드 생성
        cards = self.generate_reflection_cards(graph_results, user_context)
        
        # 상태 업데이트 - 3개 카드를 하나의 content로 통합
        combined_content = "\n\n".join([
            f"### {card.title}\n{card.content}"
            for card in cards
        ])
        
        # insights 구조 생성 (스키마 호환성 유지)
        insights = {
            "problem": graph_results[0].get("problem", "청년 문제") if graph_results else "청년 문제",
            "causes": [],
            "solutions": [],
            "supporters": [],
            "peers": []
        }
        
        # 각 카드에서 정보 수집
        for i, result in enumerate(graph_results[:3]):
            if result.get("contexts"):
                insights["causes"].extend(result["contexts"][:2])
            if result.get("initiatives"):
                insights["solutions"].extend(result["initiatives"][:2])
            if result.get("stakeholders"):
                insights["supporters"].extend(result["stakeholders"][:2])
            if result.get("affected_groups"):
                insights["peers"].extend(result["affected_groups"][:2])
        
        # 중복 제거
        insights["causes"] = list(set(insights["causes"]))[:3]
        insights["solutions"] = list(set(insights["solutions"]))[:3]
        insights["supporters"] = list(set(insights["supporters"]))[:2]
        insights["peers"] = list(set(insights["peers"]))[:2]
        
        state["reflection_card"] = {
            "content": combined_content,
            "insights": insights,
            "cards": [
                {
                    "title": card.title,
                    "content": card.content,
                    "news_id": card.news_id,
                    "news_title": card.news_title,
                    "news_date": card.news_date,
                    "key_points": card.key_points
                }
                for card in cards
            ]
        }
        state["reflection_completed"] = True
        
        return state