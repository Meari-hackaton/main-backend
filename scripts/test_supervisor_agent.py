import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from app.services.ai.agents.supervisor_agent import SupervisorAgent

def test_supervisor():
    """SupervisorAgent 테스트"""
    print("=" * 50)
    print("SupervisorAgent 테스트")
    print("=" * 50)
    
    agent = SupervisorAgent()
    
    # 테스트 케이스
    test_cases = [
        {
            "name": "초기 분석 요청",
            "data": {
                "endpoint": "/api/meari-sessions",
                "tag_ids": [2, 6],  # 번아웃, 우울감
                "user_context": "요즘 너무 힘들어요"
            }
        },
        {
            "name": "성장 콘텐츠 요청",
            "data": {
                "endpoint": "/api/growth-contents",
                "context": "initial",
                "previous_policy_ids": [],
                "persona": {"depth": "surface"}
            }
        },
        {
            "name": "리츄얼 기록",
            "data": {
                "endpoint": "/api/rituals",
                "diary_entry": "오늘은 좀 나아진 것 같아요",
                "selected_mood": "neutral",
                "growth_contents_viewed": ["info_1", "exp_1"]
            }
        },
        {
            "name": "타입으로 판단",
            "data": {
                "type": "initial",
                "tag_ids": [10],  # 사회적 고립감
                "user_context": "혼자인 것 같아"
            }
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}: {test['name']}]")
        print(f"요청 데이터: {test['data']}")
        
        # 라우팅 결정
        routing = agent.route_request(test['data'])
        
        print(f"\n라우팅 결과:")
        print(f"  - 요청 타입: {routing.request_type}")
        print(f"  - 필요 에이전트: {routing.required_agents}")
        print(f"  - 병렬 실행: {routing.parallel_execution}")
        print(f"  - 컨텍스트: {routing.context}")
        
        print("-" * 50)
    
    # LangGraph 상태 처리 테스트
    print("\n[LangGraph 상태 처리 테스트]")
    
    # 초기 분석 상태
    state = {
        "endpoint": "/api/meari-sessions",
        "tag_ids": [2],
        "user_context": "번아웃이 심해요"
    }
    
    print(f"입력 상태: {state}")
    
    # 상태 처리
    updated_state = agent.process(state)
    
    print(f"\n업데이트된 상태:")
    print(f"  - 라우팅 타입: {updated_state['routing']['type']}")
    print(f"  - 실행 계획: {updated_state.get('execution_plan', [])}")
    print(f"  - 에이전트 목록: {updated_state['routing']['agents']}")
    
    # 다음 노드 결정 테스트
    print(f"\n[다음 노드 결정 테스트]")
    
    test_states = [
        {"routing": {"type": "initial_session"}, "empathy_completed": False},
        {"routing": {"type": "initial_session"}, "empathy_completed": True, "cypher_completed": False},
        {"routing": {"type": "initial_session"}, "empathy_completed": True, "cypher_completed": True, "reflection_completed": False},
        {"routing": {"type": "growth_content"}, "growth_completed": False},
        {"routing": {"type": "ritual"}, "persona_completed": False}
    ]
    
    for state in test_states:
        next_node = agent.should_continue(state)
        print(f"  상태: {state['routing']['type']}, 다음: {next_node}")
    
    print("\n✓ 테스트 완료!")

if __name__ == "__main__":
    test_supervisor()