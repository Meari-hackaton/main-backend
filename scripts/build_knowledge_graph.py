import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document
from langchain_community.graphs.graph_document import Node, Relationship, GraphDocument

sys.path.append(str(Path(__file__).parent.parent))
from app.models.news import News
from app.models.tag import Tag

load_dotenv()

class KnowledgeGraphBuilder:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USER")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        database_url = os.getenv("DATABASE_URL")
        self.engine = create_engine(database_url.replace("asyncpg", "psycopg2"))
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",  # 일일 1,000개 제한
            temperature=0.1,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            system_instruction="""
한국 청년들의 심리적, 사회적 문제를 분석하는 전문가로서 뉴스를 분석하여 지식 그래프를 구축하세요.

## 노드(Node) 추출 규칙

### 1. Problem (문제)
- 정의: 청년이 겪는 구체적 문제, 어려움, 고민
- 예시: "청년 우울증", "취업난", "주거 불안정", "경제적 어려움", "번아웃", "사회적 고립"
- 추출 기준: 부정적 감정, 어려움, 문제점, 스트레스, 불안 관련 표현

### 2. Context (맥락적 요인)
- 정의: 문제가 발생하는 사회적/경제적/문화적 배경
- 예시: "경제 침체", "코로나19 여파", "고용시장 악화", "세대 갈등", "경쟁 사회"
- 추출 기준: 시대적 상황, 환경적 요인, 구조적 문제

### 3. Initiative (해결 시도)
- 정의: 문제 해결을 위한 정책, 프로그램, 서비스, 지원
- 예시: "청년 일자리 정책", "심리상담 프로그램", "주거지원 사업", "멘탈헬스 서비스"
- 추출 기준: 지원, 정책, 프로그램, 서비스, 대책, 해결방안 관련 표현

### 4. Stakeholder (이해관계자)
- 정의: 문제와 관련된 기관, 단체, 조직
- 예시: "고용노동부", "청년재단", "서울시", "대학교", "기업", "병원"
- 추출 기준: 기관명, 단체명, 조직명 (정확한 명칭 사용)

### 5. Cohort (집단)
- 정의: 특정 특성을 공유하는 집단, 영향받는 그룹
- 예시: "20대 청년", "구직자", "대학생", "MZ세대", "취준생", "사회초년생"
- 추출 기준: 연령대, 직업군, 세대 구분, 특정 상황의 사람들

## 관계(Relationship) 추출 규칙

### 1. CAUSES (원인 관계)
- A가 B의 원인이 됨
- 식별 패턴: "~때문에", "~로 인해", "~이 원인이 되어", "~에서 비롯된"
- 예시: "취업난" CAUSES "우울증"

### 2. ADDRESSES (해결 관계)
- A가 B를 해결하거나 다루려고 함
- 식별 패턴: "~을 위한", "~에 대응하여", "~을 해결하기 위해", "~을 지원하는"
- 예시: "일자리 정책" ADDRESSES "취업난"

### 3. INVOLVES (포함 관계)
- A가 B를 포함하거나 B가 A에 참여
- 식별 패턴: "~가 참여", "~을 대상으로", "~을 포함", "~와 함께"
- 예시: "조사" INVOLVES "청년 1000명"

### 4. AFFECTS (영향 관계)
- A가 B에 영향을 미침
- 식별 패턴: "~에 영향", "~가 겪는", "~에게 미치는", "~로 고통받는"
- 예시: "경제침체" AFFECTS "청년층"

## 중요 지침
1. 노드 이름은 명확하고 간결하게 (3-10자 권장)
2. 동일한 개념은 하나의 노드로 통합 (예: "청년 우울"과 "청년 우울증"은 "청년 우울증"으로 통일)
3. 추측이나 가정 없이 명시된 내용만 추출
4. 한국어로 정확하게 표현
5. 관계는 논리적으로 명확한 것만 추출
"""
        )
        # LLMGraphTransformer 설정
        self.transformer = LLMGraphTransformer(
            llm=self.llm,
            allowed_nodes=["Problem", "Context", "Initiative", "Stakeholder", "Cohort"],
            allowed_relationships=["CAUSES", "ADDRESSES", "INVOLVES", "AFFECTS"],
            strict_mode=False
        )
    
    def close(self):
        self.driver.close()
    
    def clear_graph(self, skip=False):
        """그래프 DB 초기화"""
        if skip:
            print("✓ 그래프 DB 초기화 건너뜀 (이어서 처리)")
            return
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ 그래프 DB 초기화 완료")
    
    def create_indexes(self):
        """인덱스 생성"""
        with self.driver.session() as session:
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (p:Problem) ON (p.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Context) ON (c.name)",
                "CREATE INDEX IF NOT EXISTS FOR (i:Initiative) ON (i.name)",
                "CREATE INDEX IF NOT EXISTS FOR (s:Stakeholder) ON (s.name)",
                "CREATE INDEX IF NOT EXISTS FOR (co:Cohort) ON (co.name)",
                "CREATE INDEX IF NOT EXISTS FOR (n:News) ON (n.news_id)"
            ]
            for index in indexes:
                session.run(index)
            print("✓ 인덱스 생성 완료")
    
    def create_news_document(self, news) -> Document:
        """뉴스를 LangChain Document로 변환"""
        content = f"""
제목: {news.title}

본문: {news.content}

핵심 내용: {news.hilight or ''}
"""
        
        metadata = {
            "news_id": news.news_id,
            "title": news.title,
            "published_at": str(news.published_at),
            "provider": news.provider
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def save_graph_to_neo4j(self, news, graph_documents: List[GraphDocument]):
        """Neo4j에 그래프 저장"""
        with self.driver.session() as session:
            # 뉴스 노드 생성 (Graph RAG용 핵심 정보 + tag_id)
            session.run(
                """
                MERGE (n:News {news_id: $news_id})
                SET n.title = $title,
                    n.content = $content,
                    n.hilight = $hilight,
                    n.published_at = $published_at,
                    n.tag_id = $tag_id
                """,
                news_id=news.news_id,
                title=news.title,
                content=news.content,
                hilight=news.hilight or "",
                published_at=str(news.published_at),
                tag_id=news.tag_id
            )
            
            # 각 GraphDocument 처리
            for doc in graph_documents:
                # 노드 생성
                for node in doc.nodes:
                    query = f"""
                    MERGE (n:{node.type} {{id: $id}})
                    ON CREATE SET n.name = $id
                    WITH n
                    MATCH (news:News {{news_id: $news_id}})
                    MERGE (news)-[:CONTAINS]->(n)
                    """
                    session.run(
                        query,
                        id=node.id,
                        news_id=news.news_id
                    )
                
                # 관계 생성
                for rel in doc.relationships:
                    query = f"""
                    MATCH (a {{id: $source}})
                    MATCH (b {{id: $target}})
                    MERGE (a)-[r:{rel.type}]->(b)
                    """
                    session.run(
                        query,
                        source=rel.source.id,
                        target=rel.target.id
                    )
    
    def process_news(self, limit: int = 10, offset: int = 284):
        """뉴스 데이터 처리"""
        with Session(self.engine) as session:
            # 샘플 뉴스 가져오기 (52개 건너뛰기)
            stmt = select(News).offset(offset).limit(limit)
            news_items = session.execute(stmt).scalars().all()
            
            print(f"\n총 {len(news_items)}개 뉴스 처리 시작")
            print("-" * 50)
            
            for idx, news in enumerate(news_items, 1):
                print(f"\n[{idx}/{len(news_items)}] {news.title[:50]}...")
                
                try:
                    # Document 생성
                    document = self.create_news_document(news)
                    
                    # 그래프 변환
                    graph_documents = self.transformer.convert_to_graph_documents([document])
                    
                    if graph_documents:
                        # Neo4j에 저장
                        self.save_graph_to_neo4j(news, graph_documents)
                        
                        # 통계 출력
                        total_nodes = sum(len(doc.nodes) for doc in graph_documents)
                        total_rels = sum(len(doc.relationships) for doc in graph_documents)
                        print(f"  ✓ 노드 {total_nodes}개, 관계 {total_rels}개 저장")
                    else:
                        print(f"  ✗ 그래프 추출 실패")
                    
                except Exception as e:
                    print(f"  ✗ 처리 중 오류: {e}")
                
                # API 제한 고려 (분당 15개 제한, 안전하게 10개)
                time.sleep(6)  # 60초/10개 = 6초
    
    def show_statistics(self):
        """통계 표시"""
        with self.driver.session() as session:
            stats = {}
            
            # 노드 타입별 개수
            node_types = ["Problem", "Context", "Initiative", "Stakeholder", "Cohort", "News"]
            for node_type in node_types:
                result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                stats[node_type] = result.single()["count"]
            
            # 관계 타입별 개수
            rel_types = ["CAUSES", "ADDRESSES", "INVOLVES", "AFFECTS", "CONTAINS"]
            for rel_type in rel_types:
                result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                stats[rel_type] = result.single()["count"]
            
            print("\n" + "=" * 50)
            print("그래프 DB 통계")
            print("=" * 50)
            print("\n[노드]")
            for node_type in node_types:
                print(f"  {node_type}: {stats[node_type]}개")
            print("\n[관계]")
            for rel_type in rel_types:
                print(f"  {rel_type}: {stats[rel_type]}개")

def main():
    builder = KnowledgeGraphBuilder()
    
    try:
        print("=" * 50)
        print("지식 그래프 구축 시작")
        print("=" * 50)
        
        # 그래프 초기화 (이어서 처리시 주석)
        # builder.clear_graph()  # 이미 52개 있으므로 건너뜀
        
        # 인덱스 생성
        builder.create_indexes()
        
        # 뉴스 처리 (52개 이후부터)
        builder.process_news(limit=1000)
        
        # 통계 표시
        builder.show_statistics()
        
        print("\n✓ 지식 그래프 구축 완료!")
        
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
    finally:
        builder.close()

if __name__ == "__main__":
    main()