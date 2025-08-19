import os
import sys
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

def check_graph_status():
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    with driver.session() as session:
        print("=" * 50)
        print("Neo4j 그래프 상태 확인")
        print("=" * 50)
        
        # 노드 타입별 개수
        node_types = ["Problem", "Context", "Initiative", "Stakeholder", "Cohort", "News"]
        print("\n[노드 통계]")
        for node_type in node_types:
            result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"  {node_type}: {count}개")
        
        # 관계 타입별 개수
        rel_types = ["CAUSES", "ADDRESSES", "INVOLVES", "AFFECTS", "CONTAINS"]
        print("\n[관계 통계]")
        for rel_type in rel_types:
            result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
            count = result.single()["count"]
            print(f"  {rel_type}: {count}개")
        
        # tag_id가 있는 뉴스 개수
        print("\n[태그별 뉴스]")
        for tag_id in range(1, 10):
            result = session.run("MATCH (n:News {tag_id: $tag_id}) RETURN count(n) as count", tag_id=tag_id)
            count = result.single()["count"]
            if count > 0:
                print(f"  태그 {tag_id}: {count}개")
        
        print("\n" + "=" * 50)
    
    driver.close()

if __name__ == "__main__":
    check_graph_status()