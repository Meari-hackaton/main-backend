import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from app.services.ai.agents.cypher_agent import CypherAgent

def test_cypher_agent():
    """CypherAgent 테스트"""
    print("=" * 50)
    print("CypherAgent 테스트")
    print("=" * 50)
    
    agent = CypherAgent()
    
    # 테스트 케이스
    test_cases = [
        {
            "question": "번아웃의 원인은 무엇인가?",
            "tag_id": None
        },
        {
            "question": "취업 문제를 해결하는 방법은?",
            "tag_id": None
        },
        {
            "question": "우울증과 관련된 모든 요소를 보여줘",
            "tag_id": 6  # 우울감/무기력 태그 (수정됨)
        },
        {
            "question": "직장 내 번아웃 문제와 해결책",
            "tag_id": 2  # 직장 내 번아웃 태그 (수정됨)
        },
        {
            "question": "사회적 고립감을 해결하는 방법",
            "tag_id": 10  # 사회적 고립감 태그 (새로 추가)
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}]")
        print(f"질문: {test['question']}")
        if test['tag_id']:
            print(f"태그 ID: {test['tag_id']}")
        
        # Cypher 쿼리 생성
        cypher_result = agent.generate_query(
            test['question'], 
            test['tag_id']
        )
        
        print(f"\n생성된 Cypher 쿼리:")
        print("-" * 30)
        print(cypher_result.query)
        print("-" * 30)
        
        # 쿼리 실행
        results = agent.execute_query(cypher_result.query)
        
        print(f"\n실행 결과: {len(results)}개 레코드")
        for j, result in enumerate(results[:3], 1):  # 처음 3개만 출력
            print(f"  {j}. {result}")
        
        if len(results) > 3:
            print(f"  ... 외 {len(results)-3}개")
        
        print("=" * 50)
    
    # LangGraph 상태 처리 테스트
    print("\n[LangGraph 상태 처리 테스트]")
    state = {
        "reflection_query": "번아웃을 해결하는 정책과 프로그램",
        "tag_id": 2  # 직장 내 번아웃 태그로 수정
    }
    
    updated_state = agent.process(state)
    
    print(f"입력 상태: {state}")
    print(f"\n생성된 쿼리: {updated_state.get('cypher_query')}")
    print(f"결과 개수: {len(updated_state.get('graph_results', []))}")
    print(f"설명: {updated_state.get('graph_explanation')}")
    
    agent.close()
    print("\n✓ 테스트 완료!")

if __name__ == "__main__":
    test_cypher_agent()