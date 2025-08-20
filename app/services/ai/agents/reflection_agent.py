from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models.news import News
import os


class InsightCard(BaseModel):
    """개별 인사이트 카드"""
    title: str = Field(description="카드 제목")
    content: str = Field(description="카드 내용 (200-300자)")
    news_id: Optional[str] = Field(description="관련 뉴스 ID")
    news_title: Optional[str] = Field(description="관련 뉴스 제목")
    news_provider: Optional[str] = Field(description="언론사")
    news_date: Optional[str] = Field(description="관련 뉴스 날짜")
    news_link: Optional[str] = Field(description="뉴스 링크")
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
        
        # 동기 데이터베이스 연결 설정
        database_url = os.getenv("DATABASE_URL")
        if database_url and "asyncpg" in database_url:
            database_url = database_url.replace("postgresql+asyncpg", "postgresql")
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _get_news_info_sync(self, news_id: str) -> Dict[str, Any]:
        """뉴스 ID로 뉴스 정보 조회 (동기 버전)"""
        if not news_id:
            return {}
        
        with self.SessionLocal() as session:
            result = session.execute(
                select(News).where(News.news_id == news_id)
            )
            news = result.scalar_one_or_none()
            if news:
                return {
                    "title": news.title,
                    "provider": news.provider,
                    "published_at": news.published_at.strftime("%Y년 %m월 %d일") if news.published_at else "",
                    "link_url": news.link_url
                }
        return {}
    
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

## 응답 형식:
반드시 다음과 같은 JSON 배열 형식으로만 응답하세요:
[
  {{
    "title": "카드 제목",
    "content": "카드 내용 (200-300자)",
    "key_points": ["포인트1", "포인트2", "포인트3"]
  }},
  {{
    "title": "카드 제목",
    "content": "카드 내용 (200-300자)",
    "key_points": ["포인트1", "포인트2", "포인트3"]
  }},
  {{
    "title": "카드 제목",
    "content": "카드 내용 (200-300자)",
    "key_points": ["포인트1", "포인트2", "포인트3"]
  }}
]"""
        
        human_template = """다음 3개의 그래프 분석 결과로 각각 다른 인사이트 카드를 작성하세요:

{graph_results}

사용자 상황: {user_context}

위의 JSON 형식으로만 응답하세요. 다른 설명은 추가하지 마세요:"""
        
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
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({
                "graph_results": str(formatted_results),
                "user_context": user_context
            })
            
            # 응답 파싱하여 카드 생성
            import json
            # response.content에서 JSON만 추출 (혹시 다른 텍스트가 있을 경우)
            content = response.content.strip()
            if content.startswith('[') and content.endswith(']'):
                cards_data = json.loads(content)
            else:
                # JSON 배열 부분만 추출 시도
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx != -1 and end_idx > start_idx:
                    cards_data = json.loads(content[start_idx:end_idx])
                else:
                    raise ValueError("JSON 배열을 찾을 수 없음")
            
            cards = []
            card_titles = [
                "뉴스가 말해주는 진짜 이유",
                "왜 이런 일이 생기는 걸까요?", 
                "희망적인 변화들도 있어요"
            ]
            
            for i, (result, title) in enumerate(zip(graph_results[:3], card_titles)):
                card_data = cards_data[i] if i < len(cards_data) else {}
                
                # 뉴스 정보 조회
                news_id = result.get("news_id")
                if news_id:
                    news_info = self._get_news_info_sync(news_id)
                else:
                    news_info = {}
                
                card = InsightCard(
                    title=card_data.get("title", title),
                    content=card_data.get("content", f"{result.get('problem', '문제')}에 대한 분석"),
                    news_id=news_id,
                    news_title=news_info.get("title") or result.get("news_title"),
                    news_provider=news_info.get("provider"),
                    news_date=news_info.get("published_at") or result.get("news_date"),
                    news_link=news_info.get("link_url"),  # PostgreSQL에서만 가져옴
                    key_points=card_data.get("key_points", [
                        f"{result.get('contexts', [''])[0]}" if result.get('contexts') else "사회적 요인",
                        f"{result.get('initiatives', [''])[0]}" if result.get('initiatives') else "해결 노력",
                        f"{result.get('affected_groups', [''])[0]}" if result.get('affected_groups') else "함께하는 사람들"
                    ])[:3]
                )
                cards.append(card)
                
            return cards
            
        except Exception as e:
            print(f"카드 생성 실패: {e}")
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
        """폴백 카드 생성 - 각각 다른 관점으로 작성"""
        cards = []
        
        # 3개의 다른 관점으로 카드 생성
        if len(graph_results) > 0:
            # 카드 1: 문제의 원인 분석
            result = graph_results[0]
            problem = result.get('problem', '직장 내 스트레스')
            contexts = result.get('contexts', ['경쟁적 직장 문화', '과도한 업무량'])
            
            content1 = f"많은 직장인들이 {problem} 문제로 고통받고 있습니다. "
            content1 += f"전문가들은 {contexts[0]}이(가) 주요 원인이라고 지적합니다. "
            if len(contexts) > 1:
                content1 += f"또한 {contexts[1]} 역시 중요한 요인으로 작용하고 있습니다. "
            content1 += "이는 개인의 문제가 아닌 우리 사회가 함께 해결해야 할 구조적 문제입니다."
            
            # 뉴스 정보 조회
            news_id = result.get("news_id")
            if news_id:
                news_info = self._get_news_info_sync(news_id)
            else:
                news_info = {}
            
            cards.append(InsightCard(
                title="뉴스가 말해주는 진짜 이유",
                content=content1[:300],
                news_id=news_id,
                news_title=news_info.get("title") or result.get("news_title"),
                news_provider=news_info.get("provider"),
                news_date=news_info.get("published_at") or result.get("news_date"),
                news_link=news_info.get("link_url"),
                key_points=[
                    f"핵심 원인: {contexts[0]}" if contexts else "구조적 문제",
                    f"추가 요인: {contexts[1]}" if len(contexts) > 1 else "복합적 요인",
                    "개인이 아닌 사회 문제"
                ]
            ))
        
        if len(graph_results) > 1:
            # 카드 2: 같은 처지의 사람들
            result = graph_results[1] if len(graph_results) > 1 else graph_results[0]
            affected = result.get('affected_groups', ['청년 직장인', 'MZ세대'])
            problem = result.get('problem', '번아웃')
            
            content2 = f"당신만 겪는 일이 아닙니다. {affected[0]}을(를) 비롯해 "
            if len(affected) > 1:
                content2 += f"{affected[1]} 등 "
            content2 += f"많은 사람들이 비슷한 {problem} 문제를 경험하고 있습니다. "
            content2 += "최근 조사에 따르면 직장인 10명 중 7명이 업무 스트레스를 호소하고 있습니다. "
            content2 += "우리는 함께 이 문제를 극복해 나갈 수 있습니다."
            
            # 뉴스 정보 조회
            news_id = result.get("news_id")
            if news_id:
                news_info = self._get_news_info_sync(news_id)
            else:
                news_info = {}
            
            cards.append(InsightCard(
                title="왜 이런 일이 생기는 걸까요?",
                content=content2[:300],
                news_id=news_id,
                news_title=news_info.get("title") or result.get("news_title"),
                news_provider=news_info.get("provider"),
                news_date=news_info.get("published_at") or result.get("news_date"),
                news_link=news_info.get("link_url"),
                key_points=[
                    f"{affected[0]} 공통 경험" if affected else "많은 이들의 경험",
                    "사회적 현상으로 인식",
                    "함께 극복 가능"
                ]
            ))
        
        if len(graph_results) > 2:
            # 카드 3: 해결 노력과 지원
            result = graph_results[2] if len(graph_results) > 2 else graph_results[0]
            initiatives = result.get('initiatives', ['근로자지원프로그램', '정신건강 상담'])
            stakeholders = result.get('stakeholders', ['고용노동부', '보건복지부'])
            
            content3 = f"다행히 사회적 관심이 높아지면서 {initiatives[0]} 같은 "
            content3 += "실질적인 지원이 확대되고 있습니다. "
            if stakeholders:
                content3 += f"{stakeholders[0]}을(를) 비롯한 여러 기관에서 "
            content3 += "청년들의 정신건강 개선을 위해 노력하고 있습니다. "
            if len(initiatives) > 1:
                content3 += f"{initiatives[1]} 서비스도 이용 가능합니다. "
            content3 += "도움이 필요할 때 주저하지 말고 지원을 받으세요."
            
            # 뉴스 정보 조회
            news_id = result.get("news_id")
            if news_id:
                news_info = self._get_news_info_sync(news_id)
            else:
                news_info = {}
            
            cards.append(InsightCard(
                title="희망적인 변화들도 있어요",
                content=content3[:300],
                news_id=news_id,
                news_title=news_info.get("title") or result.get("news_title"),
                news_provider=news_info.get("provider"),
                news_date=news_info.get("published_at") or result.get("news_date"),
                news_link=news_info.get("link_url"),
                key_points=[
                    f"{initiatives[0]} 운영 중" if initiatives else "지원 확대",
                    f"{stakeholders[0]} 지원" if stakeholders else "정부 지원",
                    "도움 요청 가능"
                ]
            ))
        
        # 결과가 부족한 경우 기본 카드 추가
        while len(cards) < 3:
            cards.append(self._generate_default_cards()[len(cards)])
        
        return cards
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        # CypherAgent 결과 가져오기
        graph_results = state.get("graph_results", [])
        user_context = state.get("user_context", "")
        
        # 디버깅: graph_results 확인
        print(f"\n=== ReflectionAgent: graph_results 받음 ===")
        print(f"graph_results 개수: {len(graph_results)}")
        if graph_results:
            print(f"첫 번째 결과: {graph_results[0]}")
        else:
            print("graph_results가 비어있음!")
        
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
                    "news_provider": card.news_provider,
                    "news_date": card.news_date,
                    "news_link": card.news_link,
                    "key_points": card.key_points
                }
                for card in cards
            ]
        }
        state["reflection_completed"] = True
        
        return state