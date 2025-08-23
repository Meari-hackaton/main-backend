#!/usr/bin/env python
"""
Neo4j 로컬 데이터를 Aura Free로 마이그레이션
"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# 로컬 Neo4j
LOCAL_URI = "bolt://localhost:7687"
LOCAL_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD", "meari_password"))

# Aura Cloud
CLOUD_URI = os.getenv("NEO4J_URI")
CLOUD_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

def migrate_data():
    """로컬 Neo4j에서 Aura로 데이터 마이그레이션"""
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=LOCAL_AUTH)
    cloud_driver = GraphDatabase.driver(CLOUD_URI, auth=CLOUD_AUTH)
    
    try:
        # 연결 확인
        local_driver.verify_connectivity()
        logger.info("✅ 로컬 Neo4j 연결 성공")
        
        cloud_driver.verify_connectivity()
        logger.info("✅ Aura 연결 성공")
        
        with local_driver.session() as local_session:
            # 1. 노드 개수 확인
            node_count = local_session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = local_session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            logger.info(f"📊 마이그레이션할 데이터: {node_count} 노드, {rel_count} 관계")
            
            # 2. 모든 노드 가져오기 (레이블별로)
            labels_result = local_session.run(
                "MATCH (n) RETURN DISTINCT labels(n) as labels"
            )
            all_labels = set()
            for record in labels_result:
                for label in record["labels"]:
                    all_labels.add(label)
            
            logger.info(f"📋 노드 레이블: {all_labels}")
            
            # 3. Aura에 노드 생성
            with cloud_driver.session() as cloud_session:
                # 기존 데이터 삭제 (선택사항)
                cloud_session.run("MATCH (n) DETACH DELETE n")
                logger.info("🗑️ Aura 기존 데이터 삭제 완료")
                
                # 레이블별로 노드 복사
                for label in all_labels:
                    nodes = local_session.run(
                        f"MATCH (n:{label}) RETURN n, id(n) as node_id"
                    ).data()
                    
                    logger.info(f"📤 {label} 노드 {len(nodes)}개 복사 중...")
                    
                    for node in tqdm(nodes, desc=f"{label} 노드"):
                        node_props = dict(node["n"])
                        node_props["_original_id"] = node["node_id"]
                        
                        # 프로퍼티 문자열 생성
                        props_str = ", ".join([f"{k}: ${k}" for k in node_props.keys()])
                        
                        cloud_session.run(
                            f"CREATE (n:{label} {{{props_str}}})",
                            **node_props
                        )
                
                # 4. 관계 복사
                logger.info("🔗 관계 복사 중...")
                
                relationships = local_session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN id(a) as start_id, id(b) as end_id, 
                           type(r) as rel_type, properties(r) as props
                """).data()
                
                for rel in tqdm(relationships, desc="관계"):
                    rel_props = rel["props"] or {}
                    
                    if rel_props:
                        props_str = ", ".join([f"{k}: ${k}" for k in rel_props.keys()])
                        query = f"""
                        MATCH (a {{_original_id: $start_id}})
                        MATCH (b {{_original_id: $end_id}})
                        CREATE (a)-[r:{rel["rel_type"]} {{{props_str}}}]->(b)
                        """
                        cloud_session.run(
                            query,
                            start_id=rel["start_id"],
                            end_id=rel["end_id"],
                            **rel_props
                        )
                    else:
                        query = f"""
                        MATCH (a {{_original_id: $start_id}})
                        MATCH (b {{_original_id: $end_id}})
                        CREATE (a)-[r:{rel["rel_type"]}]->(b)
                        """
                        cloud_session.run(
                            query,
                            start_id=rel["start_id"],
                            end_id=rel["end_id"]
                        )
                
                # 5. 임시 _original_id 제거
                cloud_session.run("MATCH (n) REMOVE n._original_id")
                
                # 6. 최종 확인
                final_nodes = cloud_session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                final_rels = cloud_session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
                
                logger.info(f"✅ 마이그레이션 완료!")
                logger.info(f"   Aura 노드: {final_nodes}")
                logger.info(f"   Aura 관계: {final_rels}")
                
    finally:
        local_driver.close()
        cloud_driver.close()


if __name__ == "__main__":
    try:
        migrate_data()
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        raise