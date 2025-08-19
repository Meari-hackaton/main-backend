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
                "output": """MATCH (p:Problem)<-[:AFFECTS]-(c:Context)
WHERE p.name CONTAINS '번아웃' OR p.id CONTAINS '번아웃'
RETURN p.name as problem, collect(DISTINCT c.name) as causes
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
    
    def execute_query(self, query: str, retry_count: int = 0) -> List[Dict[str, Any]]:
        """Cypher 쿼리 실행 (유연한 재시도 포함)"""
        with self.driver.session() as session:
            try:
                result = session.run(query)
                data = [dict(record) for record in result]
                
                # 결과가 비어있으면 None 대신 빈 리스트 반환
                return data if data else []
                
            except Exception as e:
                error_msg = str(e)
                print(f"Cypher 실행 오류 (시도 {retry_count + 1}): {error_msg}")
                
                # 구문 오류면 AI에게 다시 생성 요청
                if retry_count < 2:
                    if "SyntaxError" in error_msg or "not found" in error_msg:
                        # 에러 메시지를 포함해서 AI에게 재생성 요청
                        return self._retry_with_error_feedback(query, error_msg, retry_count + 1)
                
                return []
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        user_context = state.get("user_context", "")
        tag_ids = state.get("tag_ids", [])
        tag_id = tag_ids[0] if tag_ids else None
        
        # 1차: user_context 기반 쿼리
        if user_context:
            question = f"{user_context}와 관련된 문제와 원인, 해결책을 찾아주세요"
            cypher_result = self.generate_query(question, tag_id)
            results = self.execute_query(cypher_result.query)
            
            # user_context로 못 찾으면 태그 기반으로 재시도
            if not results or not self._has_meaningful_results(results):
                print(f"user_context로 결과 부족. 태그 {tag_id} 기반으로 재시도")
                results = self._get_tag_based_results(tag_id)
        else:
            # user_context 없으면 바로 태그 기반
            results = self._get_tag_based_results(tag_id)
        
        # 여전히 없으면 최소한의 결과라도 반환
        if not results:
            print(f"그래프 데이터 없음. 기본 Problem 반환")
            results = [{
                "problem": "청년 문제",
                "contexts": [],
                "initiatives": [],
                "stakeholders": [],
                "affected_groups": ["청년"]
            }]
        
        # 상태 업데이트
        state["cypher_query"] = cypher_result.query
        state["graph_results"] = results
        state["graph_explanation"] = cypher_result.explanation
        
        return state
    
    def _retry_with_error_feedback(self, failed_query: str, error_msg: str, retry_count: int) -> List[Dict[str, Any]]:
        """에러 피드백을 포함해서 쿼리 재생성"""
        
        # AI에게 에러 정보와 함께 재생성 요청
        retry_prompt = f"""
        다음 Cypher 쿼리가 실패했습니다:
        쿼리: {failed_query}
        에러: {error_msg}
        
        올바른 Cypher 쿼리로 수정해주세요.
        사용 가능한 노드: Problem, Context, Initiative, Stakeholder, Cohort, News
        사용 가능한 관계: CAUSES, ADDRESSES, INVOLVES, AFFECTS, CONTAINS
        """
        
        try:
            response = self.llm.invoke(retry_prompt)
            new_query = response.content.strip()
            if "```" in new_query:
                new_query = new_query.split("```")[1].replace("cypher", "").strip()
            
            print(f"재생성된 쿼리: {new_query}")
            return self.execute_query(new_query, retry_count)
            
        except Exception as e:
            print(f"쿼리 재생성 실패: {e}")
            return []
    
    def _has_meaningful_results(self, results: List[Dict]) -> bool:
        """의미있는 결과가 있는지 확인"""
        for result in results:
            # 최소한 하나의 관계라도 있으면 의미있음
            if any([
                result.get('causes', []),
                result.get('solutions', []),
                result.get('contexts', []),
                result.get('initiatives', []),
                result.get('stakeholders', []),
                result.get('affected_groups', [])
            ]):
                return True
        return False
    
    def _get_tag_based_results(self, tag_id: int) -> List[Dict[str, Any]]:
        """태그 기반으로 포괄적인 결과 가져오기"""
        if not tag_id:
            return []
        
        # 태그별 주요 키워드
        tag_keywords = {
            2: ['번아웃', '야근', '과로', '스트레스'],
            3: ['취업', '실업', '구직'],
            4: ['이직', '전직', '커리어'],
            6: ['우울', '무기력', '불안'],
            7: ['건강', '질병', '의료'],
            8: ['수면', '불면', '피로'],
            10: ['고립', '외로움', '관계'],
            11: ['세대', '갈등', '소통'],
            12: ['인간관계', '대인관계', '소통']
        }
        
        keywords = tag_keywords.get(tag_id, ['청년', '문제'])
        keyword_conditions = ' OR '.join([f'p.name CONTAINS "{kw}"' for kw in keywords])
        
        query = f"""
        MATCH (n:News {{tag_id: {tag_id}}})-[:CONTAINS]->(p:Problem)
        WHERE {keyword_conditions}
        OPTIONAL MATCH (p)<-[:AFFECTS]-(c:Context)
        OPTIONAL MATCH (p)-[:CAUSES]->(c2:Context)
        OPTIONAL MATCH (p)-[:AFFECTS]->(co:Cohort)
        OPTIONAL MATCH (i:Initiative)-[:ADDRESSES]->(p)
        OPTIONAL MATCH (s:Stakeholder)-[:INVOLVES]->(i)
        WITH p,
             collect(DISTINCT c.name) + collect(DISTINCT c2.name) as all_contexts,
             collect(DISTINCT i.name) as initiatives,
             collect(DISTINCT s.name) as stakeholders,
             collect(DISTINCT co.name) as cohorts
        RETURN 
            p.name as problem,
            all_contexts[..5] as contexts,
            initiatives[..5] as initiatives,
            stakeholders[..3] as stakeholders,
            cohorts[..3] as affected_groups
        ORDER BY size(all_contexts) + size(initiatives) DESC
        LIMIT 3
        """
        
        return self.execute_query(query)
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.close()