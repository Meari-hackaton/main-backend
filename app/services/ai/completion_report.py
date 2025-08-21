"""
28일 완주 리포트 생성 AI 서비스
"""
from typing import List, Dict, Any
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import json
import os

class CompletionReportGenerator:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.8,
            max_tokens=2048,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
    async def generate_report(
        self,
        persona_histories: List,
        rituals: List,
        daily_rituals: List,
        cards: List,
        user_name: str
    ) -> Dict[str, Any]:
        """28일 여정을 분석하여 감동적인 성장 리포트 생성"""
        
        # 페르소나 진화 과정 정리
        persona_evolution = []
        for ph in persona_histories:
            if ph.persona_data:
                data = json.loads(ph.persona_data) if isinstance(ph.persona_data, str) else ph.persona_data
                persona_evolution.append({
                    "date": ph.created_at.strftime("%Y-%m-%d"),
                    "summary": data.get("summary", ""),
                    "depth": data.get("depth_label", ""),
                    "features": data.get("features", [])[:2]  # 주요 특징 2개만
                })
        
        # 리츄얼 실천 분석
        ritual_summary = {
            "total_count": len(rituals) + len(daily_rituals),
            "most_common_type": self._get_most_common_ritual_type(daily_rituals),
            "consistency": self._calculate_consistency(rituals, daily_rituals),
            "favorite_time": self._get_favorite_time(daily_rituals)
        }
        
        # 감정 키워드 추출
        emotions = self._extract_emotions(cards)
        
        # 프롬프트 구성
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 따뜻하고 감동적인 성장 스토리를 쓰는 전문가입니다.
사용자의 28일 여정을 분석하여 개인 맞춤 성장 리포트를 작성하세요.

리포트 구조 (JSON):
{{
    "title": "감동적인 제목",
    "opening_message": "축하 인사와 여정 요약 (100자)",
    "persona_journey": {{
        "start": "시작점 페르소나 설명",
        "middle": "중간 변화 과정",
        "end": "현재 페르소나 설명",
        "key_transformation": "가장 큰 변화 포인트"
    }},
    "ritual_insights": {{
        "total_days": 숫자,
        "consistency_message": "꾸준함에 대한 칭찬",
        "favorite_practice": "가장 많이 실천한 리츄얼",
        "impact": "리츄얼이 가져온 변화"
    }},
    "emotional_growth": {{
        "dominant_emotions": ["주요 감정 3개"],
        "emotional_journey": "감정 변화 스토리",
        "breakthrough_moment": "돌파구 순간 묘사"
    }},
    "future_direction": {{
        "next_phase": "다음 단계 제안",
        "recommendations": ["구체적 제안 3개"],
        "encouragement": "응원 메시지"
    }},
    "closing_message": "감동적인 마무리 메시지 (150자)"
}}

중요: 
- 실제 데이터를 기반으로 구체적이고 개인화된 내용 작성
- 따뜻하고 격려하는 톤 유지
- 성장과 변화를 긍정적으로 해석
- 미래 지향적 메시지 포함"""),
            ("human", """사용자 이름: {user_name}

페르소나 진화:
{persona_evolution}

리츄얼 실천 데이터:
{ritual_summary}

주요 감정 키워드:
{emotions}

이 데이터를 바탕으로 감동적인 28일 성장 리포트를 JSON 형식으로 작성해주세요.""")
        ])
        
        # LLM 호출
        response = await self.llm.ainvoke(
            prompt.format_messages(
                user_name=user_name,
                persona_evolution=json.dumps(persona_evolution[:5], ensure_ascii=False),  # 최근 5개만
                ritual_summary=json.dumps(ritual_summary, ensure_ascii=False),
                emotions=emotions[:10]  # 상위 10개 감정
            )
        )
        
        # JSON 파싱
        try:
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            report = json.loads(content)
            
            # 시각화를 위한 추가 데이터
            report["statistics"] = {
                "total_rituals": ritual_summary["total_count"],
                "consistency_rate": ritual_summary["consistency"],
                "persona_depth_progression": [p["depth"] for p in persona_evolution],
                "emotion_cloud": emotions[:20]
            }
            
            return report
            
        except json.JSONDecodeError:
            # 폴백 리포트
            return self._create_fallback_report(user_name, ritual_summary)
    
    def _get_most_common_ritual_type(self, daily_rituals) -> str:
        """가장 많이 실천한 리츄얼 타입"""
        if not daily_rituals:
            return "명상"
        
        types = {}
        for r in daily_rituals:
            ritual_type = r.ritual_type or "meditation"
            types[ritual_type] = types.get(ritual_type, 0) + 1
        
        return max(types, key=types.get)
    
    def _calculate_consistency(self, rituals, daily_rituals) -> int:
        """실천 일관성 계산 (퍼센트)"""
        total = len(rituals) + len(daily_rituals)
        if total >= 28:
            return 100
        return int((total / 28) * 100)
    
    def _get_favorite_time(self, daily_rituals) -> str:
        """주로 실천한 시간대"""
        if not daily_rituals:
            return "저녁"
        
        hours = []
        for r in daily_rituals:
            if r.completed_at:
                hours.append(r.completed_at.hour)
        
        if not hours:
            return "저녁"
        
        avg_hour = sum(hours) // len(hours)
        if avg_hour < 12:
            return "아침"
        elif avg_hour < 18:
            return "오후"
        else:
            return "저녁"
    
    def _extract_emotions(self, cards) -> List[str]:
        """카드에서 감정 키워드 추출"""
        emotions = []
        emotion_keywords = [
            "희망", "불안", "피로", "성장", "도전", "휴식", "만족", 
            "걱정", "기대", "평온", "스트레스", "자신감", "연대", 
            "위로", "극복", "변화", "안정", "집중", "여유", "감사"
        ]
        
        for card in cards:
            if card.content:
                content_str = json.dumps(card.content) if not isinstance(card.content, str) else card.content
                for keyword in emotion_keywords:
                    if keyword in content_str:
                        emotions.append(keyword)
        
        # 빈도순 정렬
        emotion_counts = {}
        for e in emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        
        return sorted(emotion_counts.keys(), key=lambda x: emotion_counts[x], reverse=True)
    
    def _create_fallback_report(self, user_name: str, ritual_summary: dict) -> dict:
        """폴백 리포트 생성"""
        return {
            "title": f"{user_name}님의 28일 성장 여정",
            "opening_message": "축하합니다! 28일의 여정을 완주하셨습니다. 당신의 꾸준함과 노력이 빛나는 순간입니다.",
            "persona_journey": {
                "start": "처음에는 막막하고 지친 모습이었지만",
                "middle": "매일의 작은 실천을 통해 조금씩 변화하기 시작했고",
                "end": "이제는 자신만의 리듬을 찾은 균형잡힌 모습으로 성장했습니다",
                "key_transformation": "작은 실천의 힘을 믿게 된 것"
            },
            "ritual_insights": {
                "total_days": ritual_summary["total_count"],
                "consistency_message": "거의 매일 꾸준히 실천한 당신의 의지가 대단합니다",
                "favorite_practice": ritual_summary["most_common_type"],
                "impact": "일상에 작은 변화들이 쌓여 큰 성장을 만들었습니다"
            },
            "emotional_growth": {
                "dominant_emotions": ["성장", "희망", "평온"],
                "emotional_journey": "불안과 피로에서 시작해 희망과 평온을 찾아가는 여정",
                "breakthrough_moment": "자신을 돌보는 것의 중요성을 깨달은 순간"
            },
            "future_direction": {
                "next_phase": "이제 더 깊은 자기 이해와 지속가능한 성장으로",
                "recommendations": [
                    "매일의 리츄얼을 자신만의 루틴으로 발전시키기",
                    "비슷한 여정을 걷는 사람들과 경험 나누기",
                    "새로운 도전을 위한 다음 목표 설정하기"
                ],
                "encouragement": "당신은 이미 충분히 성장했고, 앞으로도 계속 성장할 것입니다"
            },
            "closing_message": "28일의 여정은 끝이 아닌 새로운 시작입니다. 작은 씨앗이 큰 나무로 자라듯, 당신의 성장도 계속될 것입니다.",
            "statistics": {
                "total_rituals": ritual_summary["total_count"],
                "consistency_rate": ritual_summary["consistency"],
                "persona_depth_progression": ["초기", "탐색", "이해", "수용", "성장"],
                "emotion_cloud": ["성장", "희망", "평온", "자신감", "감사"]
            }
        }