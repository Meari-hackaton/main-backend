from .base import PromptManager

def get_growth_info_prompt_manager() -> PromptManager:
    """정보 연결 성장 콘텐츠 프롬프트 매니저 생성"""
    manager = PromptManager()
    
    # 검색어 생성 프롬프트
    SEARCH_QUERY_SYSTEM = """당신은 청년의 상황을 이해하고 
필요한 정보를 찾아주는 정보 검색 전문가입니다.

주어진 페르소나와 현재 상황을 분석하여,
청년에게 도움이 될 정보를 찾기 위한 검색어를 생성하세요.

검색어 생성 원칙:
1. 구체적이고 실용적인 키워드 사용
2. 청년의 현재 관심사와 연관성
3. 해결책 중심의 검색어
4. 3-5개의 다양한 검색어 제시"""

    SEARCH_QUERY_HUMAN = """페르소나 정보:
$persona_summary

현재 상황:
- 선택한 태그: $tag_name
- 최근 관심사: $recent_interests
- 리츄얼 단계: $ritual_stage

유용한 정보를 찾기 위한 검색어를 생성해주세요."""

    manager.register_chat_template(
        name="generate_search_query",
        system=SEARCH_QUERY_SYSTEM,
        human=SEARCH_QUERY_HUMAN
    )
    
    # 정보 요약 및 구조화 프롬프트
    INFO_SUMMARY_SYSTEM = """검색된 정보를 청년에게 유용한 형태로 요약하고 구조화하세요.

구조화 형식:
1. 핵심 정보 (3줄 요약)
2. 실천 가능한 팁 (3-5개)
3. 추가 자료 링크
4. 관련 키워드

작성 원칙:
- 실용적이고 구체적인 정보
- 바로 활용 가능한 내용
- 신뢰할 수 있는 출처 명시
- 150-200자 내외"""

    INFO_SUMMARY_HUMAN = """검색 결과:
$search_results

태그: $tag_name
페르소나 특징: $persona_traits

위 정보를 구조화하여 요약해주세요."""

    manager.register_chat_template(
        name="summarize_info",
        system=INFO_SUMMARY_SYSTEM,
        human=INFO_SUMMARY_HUMAN
    )
    
    # 정보 관련성 평가 프롬프트
    INFO_RELEVANCE_SYSTEM = """주어진 정보가 청년의 현재 상황과 
얼마나 관련성이 있는지 평가하세요.

평가 기준:
1. 즉시성 (지금 당장 도움이 되는가)
2. 실용성 (실천 가능한가)
3. 맞춤성 (개인 상황과 부합하는가)
4. 신뢰성 (출처가 믿을만한가)

점수: 1-10점
이유: 간단한 설명"""

    manager.register_chat_template(
        name="evaluate_relevance",
        system=INFO_RELEVANCE_SYSTEM,
        human="정보: $info\n상황: $context"
    )
    
    return manager