from .base import PromptManager

def get_empathy_prompt_manager() -> PromptManager:
    """공감 카드 프롬프트 매니저 생성"""
    manager = PromptManager()
    
    # 공감 카드 생성 프롬프트
    EMPATHY_CARD_SYSTEM = """당신은 청년들의 마음을 깊이 이해하고 공감하는 심리 상담사입니다.
    
주어진 인용문들을 분석하여, 청년이 겪고 있는 어려움에 대해 
깊은 공감과 위로를 전하는 메시지를 작성하세요.

작성 원칙:
1. 따뜻하고 진정성 있는 어투 사용
2. 청년의 감정을 인정하고 수용
3. 비판이나 조언보다는 공감에 집중
4. 희망적이면서도 현실적인 메시지
5. 200-300자 내외로 작성

절대 하지 말아야 할 것:
- "힘내세요", "화이팅" 같은 피상적 응원
- "~해야 합니다" 같은 당위적 조언
- 문제를 축소하거나 가볍게 여기는 표현
- 비교나 경쟁을 유도하는 내용"""

    EMPATHY_CARD_HUMAN = """다음 인용문들을 읽고 공감 메시지를 작성해주세요:

인용문:
$quotes

태그: $tag_name"""

    # 프롬프트 등록
    manager.register_chat_template(
        name="empathy_card",
        system=EMPATHY_CARD_SYSTEM,
        human=EMPATHY_CARD_HUMAN
    )
    
    # 공감 표현 강화 프롬프트
    EMPATHY_ENHANCE_SYSTEM = """주어진 메시지를 더욱 공감적이고 따뜻하게 다듬어주세요.
    
개선 방향:
1. 청년의 감정을 더 구체적으로 언급
2. "당신의 마음이 ~할 것 같아요" 같은 공감 표현 추가
3. 혼자가 아님을 느낄 수 있도록"""

    manager.register_chat_template(
        name="empathy_enhance",
        system=EMPATHY_ENHANCE_SYSTEM,
        human="원본 메시지:\n$message"
    )
    
    return manager


# 프롬프트 예시 및 테스트용
EMPATHY_EXAMPLES = {
    "burnout": {
        "quotes": [
            "매일 회사 가는 게 너무 힘들어요. 아침에 눈 뜨는 것부터가 고통입니다.",
            "일의 의미를 찾을 수가 없어요. 그냥 기계처럼 반복하는 것 같아요.",
            "퇴근해도 일 생각에서 벗어날 수가 없고, 주말에도 불안해요."
        ],
        "expected_tone": "깊은 이해와 공감, 번아웃 상태 인정"
    },
    "depression": {
        "quotes": [
            "아무것도 하고 싶지 않고, 모든 게 무의미하게 느껴져요.",
            "친구들과 만나는 것도 피곤하고, 혼자 있고 싶어요.",
            "예전에 좋아했던 것들이 이제는 아무런 즐거움을 주지 않아요."
        ],
        "expected_tone": "우울감 수용, 고립감 이해"
    }
}