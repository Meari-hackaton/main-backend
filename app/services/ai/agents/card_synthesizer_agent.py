from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class CardSynthesizerAgent:
    """카드 구조화 및 DB 저장 준비 에이전트"""
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """상태를 구조화된 카드 형태로 변환"""
        
        routing_type = state.get("routing", {}).get("type", "")
        
        if routing_type == "initial_session":
            state = self._create_initial_session_cards(state)
        elif routing_type == "growth_content":
            state = self._create_growth_cards(state)
        elif routing_type == "ritual":
            state = self._create_ritual_response(state)
        
        return state
    
    def _create_initial_session_cards(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """초기 세션 카드 구조화"""
        
        # 1. 공감 카드 구조화
        empathy_card = self._structure_empathy_card(state.get("empathy_card", {}))
        
        # 2. 성찰 카드 구조화
        reflection_card = self._structure_reflection_card(state.get("reflection_card", {}))
        
        # 3. 페르소나 구조화
        persona = self._structure_persona(state.get("persona", {}))
        
        # DB 저장용 형식
        state["cards_for_db"] = [
            {
                "card_type": "empathy",
                "content": empathy_card,
                "source_ids": self._extract_source_ids(state.get("empathy_card", {}))
            },
            {
                "card_type": "reflection",
                "content": reflection_card,
                "source_ids": self._extract_graph_sources(state.get("graph_results", []))
            }
        ]
        
        # API 응답용 형식
        state["cards"] = {
            "empathy": empathy_card,
            "reflection": reflection_card
        }
        state["persona"] = persona
        
        state["final_response"] = {
            "status": "success",
            "session_type": "initial",
            "timestamp": datetime.utcnow().isoformat(),
            "cards": {
                "empathy": empathy_card,
                "reflection": reflection_card
            },
            "persona": persona,
            "next_action": "growth_content"
        }
        
        return state
    
    def _create_growth_cards(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """성장 콘텐츠 카드 구조화"""
        
        growth = state.get("growth_content", {})
        
        # 3종 카드 구조화
        info_card = self._structure_info_card(growth.get("information", {}))
        exp_card = self._structure_experience_card(growth.get("experience", {}))
        support_card = self._structure_support_card(growth.get("support", {}))
        
        # DB 저장용
        state["cards_for_db"] = [
            {
                "card_type": "growth",
                "sub_type": "information",
                "content": info_card,
                "growth_context": state.get("context_type", "initial")
            },
            {
                "card_type": "growth",
                "sub_type": "experience",
                "content": exp_card,
                "growth_context": state.get("context_type", "initial")
            },
            {
                "card_type": "growth",
                "sub_type": "support",
                "content": support_card,
                "source_ids": {"policies": [growth.get("support", {}).get("policy_id")]} if growth.get("support", {}).get("policy_id") else None
            }
        ]
        
        # API 응답용
        state["final_response"] = {
            "status": "success",
            "content_type": "growth",
            "timestamp": datetime.utcnow().isoformat(),
            "cards": {
                "information": info_card,
                "experience": exp_card,
                "support": support_card
            }
        }
        
        return state
    
    def _create_ritual_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """리츄얼 응답 구조화"""
        
        ritual_count = len(state.get("previous_rituals", []))
        tree_status = self._calculate_tree_status(ritual_count)
        
        # API 응답용
        state["final_response"] = {
            "status": "success",
            "action": "ritual_recorded",
            "timestamp": datetime.utcnow().isoformat(),
            "persona": {
                "updated": state.get("persona_completed", False),
                "depth": state.get("persona", {}).get("depth", "surface"),
                "summary": state.get("persona", {}).get("summary", "")
            },
            "tree": tree_status,
            "message": self._get_encouragement(ritual_count)
        }
        
        return state
    
    def _structure_empathy_card(self, raw_data: Dict) -> Dict[str, Any]:
        """공감 카드 구조화"""
        return {
            "type": "empathy",
            "title": "당신의 마음을 이해해요",
            "content": raw_data.get("content", ""),
            "quotes_used": raw_data.get("quotes_used", [])[:3],
            "emotion_keywords": raw_data.get("emotion_keywords", [])
        }
    
    def _structure_reflection_card(self, raw_data: Dict) -> Dict[str, Any]:
        """성찰 카드 구조화"""
        
        # insights가 이미 구조화되어 있으면 그대로 사용
        if "insights" in raw_data and isinstance(raw_data["insights"], dict):
            insights = raw_data["insights"]
        else:
            # 기존 방식으로 구조화
            insights = {
                "problem": raw_data.get("problem", ""),
                "causes": raw_data.get("contexts", [])[:3],
                "solutions": raw_data.get("initiatives", [])[:3],
                "supporters": raw_data.get("stakeholders", [])[:2],
                "peers": raw_data.get("affected_groups", [])[:2]
            }
        
        return {
            "type": "reflection",
            "title": "당신은 혼자가 아니에요",
            "content": raw_data.get("content", ""),
            "insights": insights,
            "key_message": raw_data.get("insight", "") or insights.get("key_message", "")
        }
    
    def _structure_info_card(self, raw_data: Dict) -> Dict[str, Any]:
        """정보 카드 구조화"""
        return {
            "type": "information",
            "title": raw_data.get("title", "유용한 정보"),
            "search_query": raw_data.get("search_query", ""),
            "summary": raw_data.get("content", ""),
            "sources": raw_data.get("sources", [])
        }
    
    def _structure_experience_card(self, raw_data: Dict) -> Dict[str, Any]:
        """경험 카드 구조화"""
        return {
            "type": "experience",
            "title": raw_data.get("title", "오늘의 리츄얼"),
            "activity": raw_data.get("content", ""),
            "duration": "10분 이내",
            "difficulty": "쉬움"
        }
    
    def _structure_support_card(self, raw_data: Dict) -> Dict[str, Any]:
        """지원 카드 구조화"""
        return {
            "type": "support",
            "title": raw_data.get("title", ""),
            "policy_name": raw_data.get("title", ""),
            "description": raw_data.get("content", ""),
            "organization": raw_data.get("organization", ""),
            "application_url": raw_data.get("application_url", "")
        }
    
    def _structure_persona(self, raw_data: Dict) -> Dict[str, Any]:
        """페르소나 구조화"""
        return {
            "depth": raw_data.get("depth", "surface"),
            "depth_label": self._get_depth_label(raw_data.get("depth", "surface")),
            "summary": raw_data.get("summary", ""),
            "characteristics": raw_data.get("characteristics", []),
            "needs": raw_data.get("needs", []),
            "growth_direction": raw_data.get("growth_direction", "")
        }
    
    def _calculate_tree_status(self, count: int) -> Dict[str, Any]:
        """마음나무 상태 계산"""
        
        stage_info = {
            "seed": (0, 6, "씨앗", "#8B4513"),
            "sprouting": (7, 13, "새싹", "#90EE90"),
            "growing": (14, 20, "성장", "#228B22"),
            "blooming": (21, 27, "개화", "#FF69B4"),
            "full_bloom": (28, 999, "만개", "#FF1493")
        }
        
        for stage, (min_count, max_count, label, color) in stage_info.items():
            if min_count <= count <= max_count:
                return {
                    "stage": stage,
                    "stage_label": label,
                    "progress": count,
                    "next_milestone": max_count + 1 if max_count < 28 else None,
                    "percentage": min(count / 28 * 100, 100)
                }
        
        return {"stage": "seed", "stage_label": "씨앗", "progress": 0}
    
    def _get_encouragement(self, count: int) -> str:
        """격려 메시지"""
        milestones = {
            1: "첫 걸음을 내디뎠네요!",
            7: "일주일째 함께하고 있어요.",
            14: "2주간의 여정, 대단해요!",
            21: "3주차, 거의 다 왔어요!",
            28: "완주 축하합니다!"
        }
        return milestones.get(count, f"{count}일째 성장 중!")
    
    def _get_depth_label(self, depth: str) -> str:
        """깊이 라벨"""
        labels = {
            "surface": "초기 이해",
            "understanding": "패턴 인식",
            "insight": "통찰 발견",
            "deep_insight": "깊은 이해",
            "wisdom": "통합적 지혜"
        }
        return labels.get(depth, "탐색 중")
    
    def _extract_source_ids(self, empathy_data: Dict) -> Dict[str, List[str]]:
        """공감 카드 소스 추출"""
        quotes = empathy_data.get("quotes_used", [])
        news_ids = [q.get("news_id") for q in quotes if q.get("news_id")]
        return {"news": news_ids} if news_ids else {}
    
    def _extract_graph_sources(self, graph_results: List[Dict]) -> Dict[str, List[str]]:
        """그래프 소스 추출"""
        news_ids = []
        for result in graph_results:
            if "news_id" in result:
                news_ids.append(result["news_id"])
        return {"news": list(set(news_ids))} if news_ids else {}