from .base import PromptManager

def get_persona_prompt_manager() -> PromptManager:
    """페르소나 프롬프트 매니저 생성"""
    manager = PromptManager()
    
    # 초기 페르소나 생성 프롬프트
    INITIAL_PERSONA_SYSTEM = """생성된 공감/성찰 카드 응답을 요약하여
사용자의 초기 페르소나를 생성하세요.

페르소나는 우리가 이해한 사용자 상황의 요약입니다.

형식:
- 선택 태그와 입력 컨텍스트
- 우리가 이해한 사용자의 현재 상황
- 제공한 공감과 통찰의 핵심
- 간단명료하게 2-3문장으로"""

    INITIAL_PERSONA_HUMAN = """선택한 태그: $selected_tag
사용자 입력: $user_context

생성된 응답:
- 공감 카드: $empathy_card
- 성찰 카드: $reflection_card

위 내용을 종합하여 초기 페르소나를 요약해주세요."""

    manager.register_chat_template(
        name="create_initial_persona",
        system=INITIAL_PERSONA_SYSTEM,
        human=INITIAL_PERSONA_HUMAN
    )
    
    # 페르소나 업데이트 프롬프트
    UPDATE_PERSONA_SYSTEM = """리츄얼 기록과 사용자 피드백을 바탕으로
기존 페르소나를 업데이트하세요.

업데이트 원칙:
1. 기존 페르소나의 연속성 유지
2. 새로운 정보 통합
3. 변화와 성장 반영
4. 구체화 및 세밀화

변경사항 명시:
- 추가된 내용
- 수정된 내용
- 강화된 측면"""

    UPDATE_PERSONA_HUMAN = """현재 페르소나:
$current_persona

새로운 정보:
- 리츄얼 기록: $ritual_entry
- 선택한 기분: $selected_mood
- 관심 콘텐츠: $viewed_contents
- 리츄얼 단계: $ritual_stage

업데이트된 페르소나를 생성해주세요."""

    manager.register_chat_template(
        name="update_persona",
        system=UPDATE_PERSONA_SYSTEM,
        human=UPDATE_PERSONA_HUMAN
    )
    
    # 페르소나 요약 프롬프트
    PERSONA_SUMMARY_SYSTEM = """페르소나를 간단하게 요약하세요.

요약 형식:
"[주요 고민]을 겪고 있는 [상태]한 청년으로,
[니즈]를 필요로 하며, [강점]을 가지고 있음"

길이: 50-70자
용도: API 응답 표시용, 다른 프롬프트 컨텍스트용"""

    manager.register_chat_template(
        name="summarize_persona",
        system=PERSONA_SUMMARY_SYSTEM,
        human="페르소나:\n$persona_data"
    )
    
    # 페르소나 깊이 평가 프롬프트
    PERSONA_DEPTH_SYSTEM = """페르소나의 깊이와 구체성을 평가하세요.

평가 기준:
1. 구체성 (얼마나 구체적인가)
2. 일관성 (내적 일관성)
3. 복잡성 (다면적 이해)
4. 성장성 (변화 가능성)

깊이 레벨:
- surface: 표면적 이해 (1-3일)
- understanding: 기본 이해 (4-10일)
- insight: 통찰 수준 (11-20일)
- deep: 깊은 이해 (21일+)"""

    manager.register_chat_template(
        name="evaluate_depth",
        system=PERSONA_DEPTH_SYSTEM,
        human="페르소나:\n$persona_data\n리츄얼 횟수: $ritual_count"
    )
    
    # 성장 여정 회고 프롬프트 (28일 완주 시)
    GROWTH_RETROSPECT_SYSTEM = """28일간의 페르소나 변화 히스토리를 분석하여
감동적인 성장 스토리를 작성하세요.

구성:
1. 시작점 (처음 모습)
2. 전환점 (중요한 변화 순간들)
3. 성장한 모습 (현재)
4. 앞으로의 여정

톤: 따뜻하고 감동적이며 축하하는 느낌"""

    manager.register_chat_template(
        name="create_retrospect",
        system=GROWTH_RETROSPECT_SYSTEM,
        human="전체 페르소나 히스토리:\n$persona_history"
    )
    
    return manager