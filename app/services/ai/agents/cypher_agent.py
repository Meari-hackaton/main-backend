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
        
        # Few-shot 예시 - 더 포괄적인 쿼리로 개선 (뉴스 정보 포함)
        self.examples = [
            {
                "input": "번아웃의 원인과 해결책, 관련된 모든 정보는?",
                "output": """MATCH (n:News {tag_id: 2})-[:CONTAINS]->(p:Problem)
WHERE p.name CONTAINS '번아웃'
OPTIONAL MATCH (p)<-[:AFFECTS|CAUSES]-(c:Context)
OPTIONAL MATCH (i:Initiative)-[:ADDRESSES]->(p)
OPTIONAL MATCH (s:Stakeholder)-[:INVOLVES]->(i)
OPTIONAL MATCH (p)-[:AFFECTS]->(co:Cohort)
RETURN n.news_id as news_id,
       n.title as news_title,
       n.published_at as news_date,
       p.name as problem,
       collect(DISTINCT c.name) as contexts,
       collect(DISTINCT i.name) as initiatives,
       collect(DISTINCT s.name) as stakeholders,
       collect(DISTINCT co.name) as cohorts
LIMIT 5"""
            },
            {
                "input": "취업 문제와 관련된 모든 노드와 관계는?",
                "output": """MATCH (n:News)-[:CONTAINS]->(p:Problem)
WHERE p.name CONTAINS '취업'
OPTIONAL MATCH (c:Context)-[:AFFECTS|CAUSES]->(p)
OPTIONAL MATCH (i:Initiative)-[:ADDRESSES]->(p)
OPTIONAL MATCH (s:Stakeholder)-[:INVOLVES]->(i)
OPTIONAL MATCH (p)-[:AFFECTS]->(co:Cohort)
RETURN n.news_id as news_id,
       n.title as news_title,
       n.published_at as news_date,
       p.name as problem,
       collect(DISTINCT c.name) as contexts,
       collect(DISTINCT i.name) as initiatives,
       collect(DISTINCT s.name) as stakeholders,
       collect(DISTINCT co.name) as cohorts
LIMIT 5"""
            },
            {
                "input": "문제의 원인(Context)을 찾아줘",
                "output": """MATCH (p:Problem)<-[:AFFECTS|CAUSES]-(c:Context)
RETURN p.name as problem, collect(DISTINCT c.name) as contexts
LIMIT 5"""
            },
            {
                "input": "이해관계자(Stakeholder)를 찾아줘",
                "output": """MATCH (s:Stakeholder)-[:INVOLVES|ADDRESSES|AFFECTS]-(related)
RETURN s.name as stakeholder, labels(related)[0] as related_type, collect(related.name) as related_names
LIMIT 5"""
            },
            {
                "input": "태그 2번과 관련된 포괄적인 정보",
                "output": """MATCH (n:News {tag_id: 2})-[:CONTAINS]->(node)
WITH n, labels(node)[0] as node_type, collect(DISTINCT node) as nodes
RETURN n.news_id as news_id,
       [x IN nodes WHERE 'Problem' IN labels(x) | x.name] as problems,
       [x IN nodes WHERE 'Context' IN labels(x) | x.name] as contexts,
       [x IN nodes WHERE 'Initiative' IN labels(x) | x.name] as initiatives,
       [x IN nodes WHERE 'Stakeholder' IN labels(x) | x.name] as stakeholders,
       [x IN nodes WHERE 'Cohort' IN labels(x) | x.name] as cohorts
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
5. collect()로 여러 결과 집계 가능
6. **중요**: News 노드의 news_id, title, published_at 필드를 항상 포함"""
        
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
                
                # 디버깅: 실제 쿼리 결과 확인
                if data:
                    print(f"\n=== 쿼리 실행 결과 ===")
                    print(f"결과 개수: {len(data)}")
                    print(f"첫 번째 레코드 키: {list(data[0].keys()) if data else '없음'}")
                    print(f"첫 번째 레코드 내용: {data[0] if data else '없음'}")
                
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
        """LangGraph 상태 처리 - Graph RAG"""
        user_context = state.get("user_context", "")
        tag_ids = state.get("tag_ids", [])
        tag_id = tag_ids[0] if tag_ids else None
        
        # Neo4j 연결 테스트
        try:
            with self.driver.session() as session:
                test_result = session.run("RETURN 1 as test")
                test_result.single()
                print("Neo4j 연결 성공")
        except Exception as e:
            print(f"Neo4j 연결 실패: {e}")
            # 폴백 처리
            state["cypher_query"] = "MOCK"
            state["graph_results"] = self._get_mock_results(tag_id)[:3]
            state["graph_explanation"] = "Neo4j 연결 실패 - 모의 데이터 사용"
            return state
        
        print(f"\n=== Graph RAG 시작 ===")
        print(f"사용자 컨텍스트: {user_context[:100]}...")
        print(f"태그 ID: {tag_id}")
        
        # LLM을 사용해서 자연어를 Cypher로 변환
        try:
            # 자연어 질문 생성
            question = f"{user_context}의 원인과 해결책, 관련된 모든 정보를 찾아줘"
            
            # LLM으로 Cypher 쿼리 생성
            cypher_result = self.generate_query(question, tag_id)
            generated_query = cypher_result.query
            
            print(f"\n=== LLM이 생성한 Cypher Query ===")
            print(f"Query 객체: {cypher_result}")
            print(f"Query 길이: {len(generated_query)}")
            print(f"Query 내용: {generated_query[:500] if generated_query else 'EMPTY'}")
            
            # 생성된 쿼리 실행
            print(f"쿼리 실행 시작...")
            cypher_results = self.execute_query(generated_query)
            print(f"쿼리 실행 결과: {len(cypher_results) if cypher_results else 0}개")
            
            if cypher_results and len(cypher_results) > 0:
                # LLM 생성 쿼리 성공
                structured_results = self._structure_graph_results(cypher_results)
                state["cypher_query"] = generated_query
                state["graph_results"] = structured_results
                state["graph_explanation"] = f"LLM Cypher: {len(structured_results)}개 발견"
                print(f"LLM 쿼리 성공! state에 저장됨")
            else:
                # LLM 쿼리 실패 시 최적화된 쿼리 폴백
                print(f"LLM 쿼리 실패 (결과: {cypher_results}), 최적화된 쿼리로 폴백")
                results, optimized_query = self._get_optimized_results(tag_id, user_context)
                
                if results:
                    structured_results = self._structure_graph_results(results)
                    state["cypher_query"] = optimized_query
                    state["graph_results"] = structured_results
                    state["graph_explanation"] = f"최적화 쿼리: {len(structured_results)}개 발견"
                else:
                    state["cypher_query"] = "MOCK"
                    state["graph_results"] = self._get_mock_results(tag_id)[:3]
                    state["graph_explanation"] = "모의 데이터 사용"
                    
        except Exception as e:
            print(f"LLM 쿼리 생성 실패: {e}")
            # 폴백으로 최적화된 쿼리 사용
            results, cypher_query = self._get_optimized_results(tag_id, user_context)
            
            if results:
                structured_results = self._structure_graph_results(results)
                state["cypher_query"] = cypher_query
                state["graph_results"] = structured_results
                state["graph_explanation"] = f"{len(structured_results)}개의 그래프 인사이트 발견"
            else:
                state["cypher_query"] = "MOCK"
                state["graph_results"] = self._get_mock_results(tag_id)[:3]
                state["graph_explanation"] = "모의 데이터 사용"
        
        state["cypher_completed"] = True
        print(f"최종 결과: {len(state['graph_results'])}개")
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
    
    def _get_optimized_results(self, tag_id: int, user_context: str) -> tuple[List[Dict[str, Any]], str]:
        """최적화된 쿼리로 빠르게 결과 가져오기 (쿼리도 함께 반환)"""
        if not tag_id:
            return [], "EMPTY"
        
        # 태그별 핵심 키워드 (1-2개만)
        tag_keywords = {
            2: '번아웃',
            3: '취업',
            4: '이직',
            6: '우울',
            7: '건강',
            8: '수면',
            10: '고립',
            11: '세대',
            12: '관계'
        }
        
        keyword = tag_keywords.get(tag_id, '청년')
        
        # 더 포괄적인 쿼리 - 다양한 관점 수집
        query = f"""
        // 1. 문제와 원인 분석
        MATCH (n1:News {{tag_id: {tag_id}}})-[:CONTAINS]->(p1:Problem)
        WHERE p1.name CONTAINS '{keyword}' OR p1.name CONTAINS '스트레스' OR p1.name CONTAINS '불안'
        WITH n1, p1 ORDER BY n1.published_at DESC LIMIT 1
        OPTIONAL MATCH (p1)<-[:CAUSES|AFFECTS]-(c1:Context)
        WITH n1, p1, collect(DISTINCT c1.name)[..3] as contexts1
        
        // 2. 사회적 맥락과 영향받는 집단
        MATCH (n2:News {{tag_id: {tag_id}}})-[:CONTAINS]->(p2:Problem)
        WHERE p2.name CONTAINS '{keyword}' OR p2.name CONTAINS '청년'
        WITH n1, p1, contexts1, n2, p2 ORDER BY n2.published_at DESC LIMIT 1
        OPTIONAL MATCH (p2)-[:AFFECTS]->(co:Cohort)
        OPTIONAL MATCH (ctx:Context)-[:AFFECTS|CAUSES]->(p2)
        WITH n1, p1, contexts1, n2, p2, 
             collect(DISTINCT co.name)[..2] as cohorts2,
             collect(DISTINCT ctx.name)[..2] as contexts2
        
        // 3. 해결 방안과 지원
        MATCH (n3:News {{tag_id: {tag_id}}})-[:CONTAINS]->(i:Initiative)
        WITH n1, p1, contexts1, n2, p2, cohorts2, contexts2, n3, i ORDER BY n3.published_at DESC LIMIT 1
        OPTIONAL MATCH (s:Stakeholder)-[:INVOLVES]->(i)
        OPTIONAL MATCH (i)-[:ADDRESSES]->(p3:Problem)
        WITH n1, p1, contexts1, n2, p2, cohorts2, contexts2, n3, i,
             collect(DISTINCT s.name)[..2] as stakeholders3,
             collect(DISTINCT p3.name)[..1] as problems3
        
        RETURN [
            {{
                news_id: n1.news_id,
                news_title: n1.title,
                news_date: n1.published_at,
                problem: p1.name,
                contexts: contexts1,
                initiatives: [],
                stakeholders: [],
                affected_groups: []
            }},
            {{
                news_id: n2.news_id,
                news_title: n2.title,
                news_date: n2.published_at,
                problem: p2.name,
                contexts: contexts2,
                initiatives: [],
                stakeholders: [],
                affected_groups: cohorts2
            }},
            {{
                news_id: n3.news_id,
                news_title: n3.title,
                news_date: n3.published_at,
                problem: CASE WHEN size(problems3) > 0 THEN problems3[0] ELSE i.name END,
                contexts: [],
                initiatives: [i.name],
                stakeholders: stakeholders3,
                affected_groups: []
            }}
        ] as results
        UNWIND results as result
        RETURN result.news_id as news_id,
               result.news_title as news_title,
               result.news_date as news_date,
               result.problem as problem,
               result.contexts as contexts,
               result.initiatives as initiatives,
               result.stakeholders as stakeholders,
               result.affected_groups as affected_groups
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query)
                data = [dict(record) for record in result]
                print(f"최적화된 쿼리 결과: {len(data)}개")
                
                # 결과가 3개 미만이면 폴백 쿼리 실행
                if len(data) < 3:
                    fallback_data = self._get_fallback_results(tag_id, keyword)
                    return fallback_data, query  # 쿼리도 함께 반환
                    
                return data[:3], query  # 쿼리도 함께 반환
        except Exception as e:
            print(f"쿼리 실행 실패: {e}")
            fallback_data = self._get_fallback_results(tag_id, keyword)
            return fallback_data, f"FAILED: {str(e)}"
    
    def _get_fallback_results(self, tag_id: int, keyword: str) -> List[Dict[str, Any]]:
        """폴백 쿼리 - 더 단순한 방식으로 데이터 수집"""
        try:
            # 단순한 쿼리로 최소한의 데이터라도 가져오기
            query = f"""
            MATCH (n:News {{tag_id: {tag_id}}})-[:CONTAINS]->(node)
            WHERE labels(node)[0] IN ['Problem', 'Context', 'Initiative', 'Stakeholder', 'Cohort']
            WITH n, collect(DISTINCT {{
                type: labels(node)[0],
                name: node.name
            }}) as nodes
            RETURN n.news_id as news_id,
                   n.title as news_title,
                   n.published_at as news_date,
                   nodes
            ORDER BY n.published_at DESC
            LIMIT 3
            """
            
            with self.driver.session() as session:
                result = session.run(query)
                raw_data = [dict(record) for record in result]
                
                # 데이터 구조화
                structured = []
                for record in raw_data:
                    nodes = record.get('nodes', [])
                    
                    problems = [n['name'] for n in nodes if n['type'] == 'Problem']
                    contexts = [n['name'] for n in nodes if n['type'] == 'Context']
                    initiatives = [n['name'] for n in nodes if n['type'] == 'Initiative']
                    stakeholders = [n['name'] for n in nodes if n['type'] == 'Stakeholder']
                    cohorts = [n['name'] for n in nodes if n['type'] == 'Cohort']
                    
                    structured.append({
                        'news_id': record.get('news_id'),
                        'news_title': record.get('news_title'),
                        'news_date': str(record.get('news_date')) if record.get('news_date') else None,
                        'problem': problems[0] if problems else f"{keyword} 관련 문제",
                        'contexts': contexts[:3],
                        'initiatives': initiatives[:3],
                        'stakeholders': stakeholders[:2],
                        'affected_groups': cohorts[:2]
                    })
                
                if structured:
                    return structured
                    
        except Exception as e:
            print(f"폴백 쿼리도 실패: {e}")
        
        # 최종 폴백: 모의 데이터
        return self._get_mock_results(tag_id)
    
    def _get_mock_results(self, tag_id: int) -> List[Dict[str, Any]]:
        """Neo4j 연결 실패 시 모의 데이터 반환"""
        mock_data = {
            2: [  # 직장 내 번아웃
                {
                    "problem": "번아웃",
                    "contexts": ["과도한 업무량", "성과 압박", "워라밸 부재"],
                    "initiatives": ["근로자지원프로그램(EAP)", "유연근무제", "정신건강 상담"],
                    "stakeholders": ["고용노동부", "근로복지공단"],
                    "affected_groups": ["MZ세대 직장인", "청년 근로자"]
                },
                {
                    "problem": "직무 스트레스",
                    "contexts": ["경쟁적 조직문화", "불안정한 고용", "낮은 자율성"],
                    "initiatives": ["스트레스 관리 프로그램", "조직문화 개선"],
                    "stakeholders": ["기업 인사팀", "산업안전보건공단"],
                    "affected_groups": ["신입사원", "중간관리자"]
                },
                {
                    "problem": "퇴사 고민",
                    "contexts": ["성장 기회 부족", "비전 부재", "보상 불만족"],
                    "initiatives": ["경력개발 지원", "멘토링 프로그램"],
                    "stakeholders": ["기업", "고용센터"],
                    "affected_groups": ["2-3년차 직장인"]
                }
            ]
        }
        
        return mock_data.get(tag_id, [
            {
                "problem": "청년 문제",
                "contexts": ["사회구조적 요인"],
                "initiatives": ["정부 지원 정책"],
                "stakeholders": ["관련 기관"],
                "affected_groups": ["청년층"]
            }
        ])
    
    def _generate_questions_from_context(self, user_context: str, tag_id: Optional[int] = None) -> List[str]:
        """사용자 컨텍스트에서 그래프 탐색을 위한 질문 생성"""
        
        # 태그별 핵심 키워드
        tag_focus = {
            2: "번아웃, 야근, 과로",
            3: "취업, 실업, 구직",
            4: "이직, 전직, 커리어",
            6: "우울, 무기력, 정신건강",
            7: "건강, 질병, 의료",
            8: "수면, 불면, 피로",
            10: "고립, 외로움, 관계",
            11: "세대, 갈등, 소통",
            12: "인간관계, 대인관계"
        }
        
        focus = tag_focus.get(tag_id, "청년 문제")
        
        prompt = f"""
        사용자 상황: {user_context}
        관련 주제: {focus}
        
        이 상황에서 Neo4j 그래프 DB를 탐색하기 위한 핵심 질문 3개를 생성하세요.
        각 질문은 다른 관점에서 접근해야 합니다:
        1. 문제의 원인 탐색
        2. 해결책이나 지원 탐색
        3. 영향받는 집단이나 관련 이해관계자 탐색
        
        한 줄씩 작성하세요:
        """
        
        try:
            response = self.llm.invoke(prompt)
            questions = response.content.strip().split('\n')
            # 번호나 불필요한 문자 제거
            questions = [q.strip().lstrip('1234567890.-) ') for q in questions if q.strip()]
            return questions[:3]
        except Exception as e:
            print(f"질문 생성 실패: {e}")
            # 폴백 질문들
            return [
                f"{focus}의 원인은 무엇인가?",
                f"{focus}를 해결하는 정책이나 프로그램은?",
                f"{focus}로 영향받는 집단은?"
            ]
    
    def _structure_graph_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """그래프 쿼리 결과를 구조화 (간소화)"""
        structured = []
        seen_problems = set()
        
        for result in raw_results[:3]:  # 최대 3개만 처리
            problem = result.get('problem')
            if problem and problem not in seen_problems:
                seen_problems.add(problem)
                
                structured.append({
                    'problem': problem,
                    'contexts': result.get('contexts', [])[:3],
                    'initiatives': result.get('initiatives', [])[:3],
                    'stakeholders': result.get('stakeholders', [])[:2],
                    'affected_groups': result.get('affected_groups', [])[:2],
                    'news_id': result.get('news_id'),
                    'news_title': result.get('news_title'),
                    'news_date': str(result.get('news_date')) if result.get('news_date') else None
                })
        
        return structured
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.close()