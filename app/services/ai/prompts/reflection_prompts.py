from .base import PromptManager

def get_reflection_prompt_manager() -> PromptManager:
    """성찰 카드 프롬프트 매니저 생성"""
    manager = PromptManager()
    
    # 성찰 카드 생성 프롬프트
    REFLECTION_CARD_SYSTEM = """당신은 청년들이 자신의 상황을 객관적으로 이해하고 
통찰을 얻을 수 있도록 돕는 심리 분석가입니다.

주어진 인과관계 데이터를 분석하여 구조화된 성찰 카드를 작성하세요.

카드 구성 요소:
1. 제목: 핵심 통찰을 담은 한 문장 (15자 내외)
2. 핵심 인용: 가장 중요한 인용문 1개
3. 원인 분석: 문제의 근본 원인 2-3개
4. 맥락 이해: 사회적/환경적 배경
5. 시사점: 얻을 수 있는 교훈이나 관점

작성 원칙:
- 객관적이고 분석적인 톤
- 인과관계를 명확히 드러내기
- 개인의 잘못이 아닌 구조적 문제 강조
- 새로운 관점 제시"""

    REFLECTION_CARD_HUMAN = """다음 그래프 데이터를 분석하여 성찰 카드를 작성하세요:

문제(Problems): $problems
원인(Causes): $causes  
맥락(Context): $contexts
영향받는 집단(Cohorts): $cohorts
관련 이해관계자(Stakeholders): $stakeholders

태그: $tag_name"""

    manager.register_chat_template(
        name="reflection_card",
        system=REFLECTION_CARD_SYSTEM,
        human=REFLECTION_CARD_HUMAN
    )
    
    # 인과관계 분석 강화 프롬프트
    CAUSAL_ANALYSIS_SYSTEM = """주어진 그래프 관계를 분석하여 
핵심 인과관계 체인을 추출하세요.

분석 포인트:
1. 근본 원인 → 직접 원인 → 결과의 연쇄
2. 악순환 구조 파악
3. 개입 가능한 지점 식별"""

    manager.register_chat_template(
        name="causal_analysis",
        system=CAUSAL_ANALYSIS_SYSTEM,
        human="그래프 데이터:\n$graph_data"
    )
    
    # 구조화 포맷팅 프롬프트
    STRUCTURE_FORMAT_SYSTEM = """주어진 분석 내용을 구조화된 카드 형식으로 정리하세요.

형식:
### [제목]
**핵심 인용:** "..."

**원인 분석:**
• 원인 1
• 원인 2
• 원인 3

**맥락 이해:**
[사회적/환경적 배경 설명]

**시사점:**
[개인과 사회가 얻을 수 있는 통찰]"""

    manager.register_chat_template(
        name="structure_format",
        system=STRUCTURE_FORMAT_SYSTEM,
        human="분석 내용:\n$analysis"
    )
    
    return manager


# 그래프 데이터 예시
REFLECTION_EXAMPLES = {
    "job_anxiety": {
        "problems": ["취업 불안", "자존감 하락", "미래 불확실성"],
        "causes": ["높은 경쟁률", "경기 침체", "스펙 인플레이션"],
        "contexts": ["청년 실업률 상승", "비정규직 증가"],
        "cohorts": ["취준생", "대학 4학년"],
        "stakeholders": ["대학", "기업", "정부"],
        "expected_insight": "구조적 문제로서의 취업난 이해"
    },
    "isolation": {
        "problems": ["사회적 고립", "외로움", "관계 단절"],
        "causes": ["경쟁 문화", "개인주의 심화", "디지털 소통 증가"],
        "contexts": ["1인 가구 증가", "코로나19 영향"],
        "cohorts": ["20-30대 청년", "프리랜서"],
        "stakeholders": ["지역 커뮤니티", "정신건강 기관"],
        "expected_insight": "현대 사회의 구조적 고립 메커니즘"
    }
}