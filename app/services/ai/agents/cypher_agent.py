from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from pydantic import BaseModel, Field
from neo4j import GraphDatabase
import os


class CypherQuery(BaseModel):
    """Cypher 쿼리 결과"""
    query: str = Field(description="생성된 Cypher 쿼리")
    explanation: str = Field(description="쿼리 설명")
    expected_output: str = Field(description="예상 출력 형태")


class CypherAgent:
    """자연어를 Cypher 쿼리로 변환하는 에이전트"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.1,  # 정확한 쿼리 생성을 위해 낮은 temperature
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Neo4j 연결
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        
        # Few-shot 예시
        self.examples = [
            {
                "input": "번아웃의 원인은 무엇인가?",
                "output": """MATCH (c:Context)-[:CAUSES]->(p:Problem)
WHERE p.name CONTAINS '번아웃' OR p.id CONTAINS '번아웃'
RETURN c.name as cause, p.name as problem
LIMIT 5"""
            },
            {
                "input": "취업 문제를 해결하는 정책이나 프로그램은?",
                "output": """MATCH (i:Initiative)-[:ADDRESSES]->(p:Problem)
WHERE p.name CONTAINS '취업' OR p.id CONTAINS '취업'
RETURN i.name as initiative, p.name as problem
LIMIT 5"""
            },
            {
                "input": "우울증이 영향을 미치는 집단은?",
                "output": """MATCH (p:Problem)-[:AFFECTS]->(co:Cohort)
WHERE p.name CONTAINS '우울' OR p.id CONTAINS '우울'
RETURN p.name as problem, co.name as affected_group
LIMIT 5"""
            },
            {
                "input": "청년 정책에 관련된 이해관계자는?",
                "output": """MATCH (s:Stakeholder)-[:INVOLVES]->(i:Initiative)
WHERE i.name CONTAINS '청년' OR i.id CONTAINS '청년'
RETURN s.name as stakeholder, i.name as initiative
LIMIT 5"""
            },
            {
                "input": "태그 1번과 관련된 문제와 해결책은?",
                "output": """MATCH (n:News {tag_id: 1})-[:CONTAINS]->(p:Problem)
OPTIONAL MATCH (i:Initiative)-[:ADDRESSES]->(p)
RETURN DISTINCT p.name as problem, collect(DISTINCT i.name) as solutions
LIMIT 5"""
            }
        ]
        
        self.prompt = self._create_prompt()
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """Cypher 생성 프롬프트 생성"""
        
        # Few-shot 프롬프트 설정
        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{output}")
        ])
        
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=self.examples
        )
        
        # 전체 프롬프트
        system_message = """당신은 Neo4j Cypher 쿼리 전문가입니다.
자연어 질문을 Cypher 쿼리로 변환하세요.

## 사용 가능한 노드 타입:
- Problem: 청년이 겪는 문제
- Context: 문제의 맥락적 요인
- Initiative: 해결 시도/정책/프로그램
- Stakeholder: 이해관계자/기관
- Cohort: 특정 집단
- News: 뉴스 (tag_id 속성 포함)

## 사용 가능한 관계:
- CAUSES: Context -> Problem (원인)
- ADDRESSES: Initiative -> Problem (해결)
- INVOLVES: Stakeholder -> Initiative (참여)
- AFFECTS: Problem -> Cohort (영향)
- CONTAINS: News -> 모든 노드 (포함)

## 쿼리 작성 규칙:
1. 한글 검색 시 CONTAINS 사용 (=는 정확히 일치할 때만)
2. 항상 LIMIT 설정 (기본 5-10개)
3. tag_id 필터링 가능 (1~9)
4. OPTIONAL MATCH로 없을 수도 있는 관계 처리
5. collect()로 여러 결과 집계 가능"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            few_shot_prompt,
            ("human", "{question}")
        ])
    
    def generate_query(self, question: str, tag_id: Optional[int] = None) -> CypherQuery:
        """자연어 질문을 Cypher 쿼리로 변환"""
        
        # tag_id가 있으면 질문에 포함
        if tag_id:
            question = f"태그 {tag_id}번과 관련된 {question}"
        
        # LLM으로 쿼리 생성
        chain = self.prompt | self.llm
        response = chain.invoke({"question": question})
        
        # 쿼리 정제
        query = response.content.strip()
        if "```" in query:
            # 코드 블록 제거
            query = query.split("```")[1].replace("cypher", "").strip()
        
        return CypherQuery(
            query=query,
            explanation=f"{question}에 대한 Cypher 쿼리",
            expected_output="노드와 관계 정보"
        )
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Cypher 쿼리 실행"""
        with self.driver.session() as session:
            try:
                result = session.run(query)
                return [dict(record) for record in result]
            except Exception as e:
                print(f"Cypher 실행 오류: {e}")
                return []
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        question = state.get("reflection_query", "")
        tag_id = state.get("tag_id")
        
        # Cypher 쿼리 생성
        cypher_result = self.generate_query(question, tag_id)
        
        # 쿼리 실행
        results = self.execute_query(cypher_result.query)
        
        # 상태 업데이트
        state["cypher_query"] = cypher_result.query
        state["graph_results"] = results
        state["graph_explanation"] = cypher_result.explanation
        
        return state
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.close()