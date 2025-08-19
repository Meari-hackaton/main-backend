from .base import PromptManager

def get_context_prompt_manager() -> PromptManager:
    """컨텍스트 프롬프트 매니저 생성"""
    manager = PromptManager()
    
    # Initial 컨텍스트 판단 프롬프트
    INITIAL_CONTEXT_SYSTEM = """첫 방문 사용자를 위한 콘텐츠 생성 가이드입니다.

Initial 컨텍스트 특징:
- 사용자가 처음 서비스를 이용
- 페르소나가 아직 얕음
- 모든 성장 콘텐츠 3종 필요

생성 원칙:
1. 정보: 기본적이고 포괄적인 내용
2. 경험: 부담 없는 첫 리츄얼
3. 지원: 가장 접근하기 쉬운 정책"""

    manager.register_chat_template(
        name="initial_context",
        system=INITIAL_CONTEXT_SYSTEM,
        human="태그: $tag_name\n사용자 입력: $user_context"
    )
    
    # Ritual 컨텍스트 판단 프롬프트
    RITUAL_CONTEXT_SYSTEM = """리츄얼 진행 중인 사용자를 위한 콘텐츠 생성 가이드입니다.

Ritual 컨텍스트 특징:
- 이미 리츄얼 진행 중
- 페르소나가 구체화됨
- 정책은 새로운 것만 선택적 제공

생성 원칙:
1. 정보: 개인화된 맞춤 정보
2. 경험: 이전 리츄얼과 연계된 활동
3. 지원: 이미 본 정책 제외하고 새로운 것만"""

    manager.register_chat_template(
        name="ritual_context",
        system=RITUAL_CONTEXT_SYSTEM,
        human="페르소나: $persona_summary\n리츄얼 단계: $ritual_stage\n이전 정책 ID: $previous_policy_ids"
    )
    
    # 컨텍스트 전환 판단 프롬프트
    CONTEXT_SWITCH_SYSTEM = """사용자의 상태 변화를 감지하여
적절한 컨텍스트를 판단하세요.

판단 기준:
- ritual_count = 0: initial
- ritual_count >= 1: ritual
- 특별한 이벤트 시 조정 가능"""

    manager.register_chat_template(
        name="judge_context",
        system=CONTEXT_SWITCH_SYSTEM,
        human="리츄얼 횟수: $ritual_count\n최근 활동: $recent_activity"
    )
    
    # 정책 중복 방지 프롬프트
    POLICY_DEDUP_SYSTEM = """이미 본 정책을 제외하고
새로운 정책만 선택하세요.

중복 방지 원칙:
- previous_policy_ids에 있는 것 제외
- 유사도 높은 순서로 선택
- 모두 본 경우 "더 이상 새로운 정책 없음" 반환"""

    manager.register_chat_template(
        name="deduplicate_policy",
        system=POLICY_DEDUP_SYSTEM,
        human="이전 정책 ID: $previous_policy_ids\n후보 정책: $candidate_policies"
    )
    
    return manager