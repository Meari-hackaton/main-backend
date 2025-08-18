import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

def test_neo4j_connection():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    
    print(f"Neo4j URI: {uri}")
    print(f"Neo4j User: {user}")
    print("-" * 50)
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            record = result.single()
            print(f"✓ 연결 테스트 성공: {record['num']}")
            
            result = session.run("CALL dbms.components()")
            for record in result:
                print(f"✓ Neo4j 버전: {record['name']} {record['versions'][0]}")
            
            result = session.run("SHOW DATABASES")
            print("\n데이터베이스 목록:")
            for record in result:
                print(f"  - {record['name']} (상태: {record['currentStatus']})")
        
        driver.close()
        print("\n✓ Neo4j 연결 테스트 완료!")
        
    except Exception as e:
        print(f"✗ Neo4j 연결 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_neo4j_connection()