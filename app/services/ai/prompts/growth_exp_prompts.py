from .base import PromptManager

def get_growth_exp_prompt_manager() -> PromptManager:
    """경험 연결 성장 콘텐츠 프롬프트 매니저 생성"""
    manager = PromptManager()
    
    # 리츄얼 제안 프롬프트
    RITUAL_SUGGEST_SYSTEM = """당신은 청년의 일상에 작은 변화를 만들어주는 
라이프 코치입니다.

주어진 상황과 페르소나를 고려하여,
간단한 리츄얼을 제안하세요.

리츄얼 제안 원칙:
1. 특별한 도구나 장소 불필요
2. 즉시 실천 가능
3. 구체적인 행동 단계 제시
4. 심리적 부담 최소화"""

    RITUAL_SUGGEST_HUMAN = """페르소나 정보:
$persona_summary

현재 상황:
- 선택한 태그: $tag_name
- 기분 상태: $mood_state
- 이전 리츄얼: $previous_rituals
- 리츄얼 단계: $ritual_stage

리츄얼을 제안해주세요."""

    manager.register_chat_template(
        name="suggest_ritual",
        system=RITUAL_SUGGEST_SYSTEM,
        human=RITUAL_SUGGEST_HUMAN
    )
    
    # 리츄얼 효과 설명 프롬프트
    RITUAL_EFFECT_SYSTEM = """제안된 리츄얼이 청년에게 
어떤 도움을 줄 수 있는지 설명하세요.

설명 구성:
1. 즉각적 효과 (오늘 느낄 수 있는 변화)
2. 장기적 효과 (꾸준히 했을 때)
3. 심리학적 근거 (간단히)

톤: 희망적이면서도 현실적
길이: 100자 내외"""

    RITUAL_EFFECT_HUMAN = """리츄얼: $ritual_description
태그: $tag_name

이 리츄얼의 효과를 설명해주세요."""

    manager.register_chat_template(
        name="explain_effect",
        system=RITUAL_EFFECT_SYSTEM,
        human=RITUAL_EFFECT_HUMAN
    )
    
    # 리츄얼 맞춤화 프롬프트  
    RITUAL_PERSONALIZE_SYSTEM = """기본 리츄얼을 개인의 상황에 맞게 
조정하세요.

맞춤화 고려사항:
1. 개인의 선호도 반영
2. 현재 에너지 레벨 고려
3. 시간대별 적합성
4. 이전 리츄얼과의 연계성"""

    manager.register_chat_template(
        name="personalize_ritual",
        system=RITUAL_PERSONALIZE_SYSTEM,
        human="기본 리츄얼: $base_ritual\n개인 특성: $personal_traits"
    )
    
    # 리츄얼 단계별 가이드
    RITUAL_STEPS_SYSTEM = """리츄얼을 구체적인 단계로 나누어 
실천 가이드를 작성하세요.

형식:
1단계: [구체적 행동] (30초)
2단계: [구체적 행동] (2분)
3단계: [구체적 행동] (2분)
4단계: [마무리] (30초)

각 단계는 매우 구체적이고 명확하게"""

    manager.register_chat_template(
        name="create_steps",
        system=RITUAL_STEPS_SYSTEM,
        human="리츄얼: $ritual_name\n설명: $ritual_description"
    )
    
    return manager