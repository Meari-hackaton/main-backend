from typing import Dict, Any, List, Optional, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os
import json


class Persona(BaseModel):
    """페르소나 모델"""
    depth: Literal["surface", "understanding", "insight", "deep_insight", "wisdom"] = Field(
        description="페르소나 깊이"
    )
    summary: str = Field(description="페르소나 요약")
    characteristics: List[str] = Field(description="주요 특징")
    needs: List[str] = Field(description="핵심 니즈")
    growth_direction: str = Field(description="성장 방향")


class PersonaAgent:
    """페르소나 생성 및 관리 에이전트"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.6,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.initial_prompt = self._create_initial_prompt()
        self.update_prompt = self._create_update_prompt()
    
    def _create_initial_prompt(self) -> ChatPromptTemplate:
        """초기 페르소나 생성 프롬프트"""
        
        system_message = """응답 내용을 기반으로 사용자의 초기 페르소나를 생성하세요.

## 원칙:
1. 응답에서 드러난 상황과 감정 중심
2. 판단이나 평가 없이 관찰된 사실만
3. 간결하고 명확한 표현

## 페르소나 구조:
- 요약: 1-2문장으로 핵심 상황
- 특징: 3-5개 주요 특성
- 니즈: 2-3개 핵심 필요
- 방향: 성장 가능성"""
        
        human_template = """다음 응답 내용으로 페르소나를 생성하세요:

공감 카드: {empathy_card}
성찰 카드: {reflection_card}

페르소나:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def _create_update_prompt(self) -> ChatPromptTemplate:
        """페르소나 업데이트 프롬프트"""
        
        system_message = """리츄얼 피드백을 반영하여 페르소나를 업데이트하세요.

## 원칙:
1. 기존 페르소나에서 연속성 유지
2. 새로운 패턴이나 변화 반영
3. 점진적 깊이 증가

## 깊이 단계:
- surface: 표면적 이해
- understanding: 패턴 인식
- insight: 핵심 통찰
- deep_insight: 깊은 이해
- wisdom: 통합적 지혜"""
        
        human_template = """현재 페르소나와 리츄얼 피드백으로 업데이트하세요:

현재 페르소나: {current_persona}
리츄얼 일기: {diary_entry}
선택한 감정: {selected_mood}

업데이트된 페르소나:"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template)
        ])
    
    def create_initial_persona(
        self,
        empathy_card: str,
        reflection_card: str
    ) -> Persona:
        """초기 페르소나 생성"""
        
        chain = self.initial_prompt | self.llm
        response = chain.invoke({
            "empathy_card": empathy_card,
            "reflection_card": reflection_card
        })
        
        # 응답 파싱
        content = response.content
        lines = content.strip().split("\n")
        
        # 간단한 파싱 (실제로는 더 정교한 파싱 필요)
        summary = ""
        characteristics = []
        needs = []
        direction = ""
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "요약" in line or "Summary" in line:
                current_section = "summary"
            elif "특징" in line or "특성" in line:
                current_section = "characteristics"
            elif "니즈" in line or "필요" in line:
                current_section = "needs"
            elif "방향" in line or "성장" in line:
                current_section = "direction"
            elif line.startswith("-") or line.startswith("*"):
                clean_line = line.lstrip("-*").strip()
                if current_section == "characteristics":
                    characteristics.append(clean_line)
                elif current_section == "needs":
                    needs.append(clean_line)
            elif current_section == "summary" and not summary:
                summary = line
            elif current_section == "direction" and not direction:
                direction = line
        
        return Persona(
            depth="surface",
            summary=summary or "초기 페르소나 생성됨",
            characteristics=characteristics[:5] if characteristics else ["현재 상황 파악 중", "감정 상태 관찰 중", "니즈 분석 중"],
            needs=needs[:3] if needs else ["정서적 지지", "상황 이해", "실질적 도움"],
            growth_direction=direction if direction else "자기 이해와 수용을 통한 점진적 회복"
        )
    
    def update_persona(
        self,
        current_persona: Persona,
        diary_entry: str,
        selected_mood: str
    ) -> Persona:
        """페르소나 업데이트"""
        
        chain = self.update_prompt | self.llm
        response = chain.invoke({
            "current_persona": json.dumps({
                "depth": current_persona.depth,
                "summary": current_persona.summary,
                "characteristics": current_persona.characteristics,
                "needs": current_persona.needs,
                "growth_direction": current_persona.growth_direction
            }, ensure_ascii=False),
            "diary_entry": diary_entry,
            "selected_mood": selected_mood
        })
        
        # 깊이 업데이트
        depth_progression = {
            "surface": "understanding",
            "understanding": "insight",
            "insight": "deep_insight",
            "deep_insight": "wisdom",
            "wisdom": "wisdom"
        }
        new_depth = depth_progression.get(current_persona.depth, "surface")
        
        # 응답 파싱 (간단한 버전)
        content = response.content
        
        # 기존 페르소나 기반으로 업데이트
        return Persona(
            depth=new_depth,
            summary=content.split("\n")[0] if content else current_persona.summary,
            characteristics=current_persona.characteristics,  # 유지하거나 업데이트
            needs=current_persona.needs,  # 유지하거나 업데이트
            growth_direction=current_persona.growth_direction  # 유지하거나 업데이트
        )
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 상태 처리"""
        
        routing_type = state.get("routing", {}).get("type", "")
        
        if routing_type == "initial_session":
            # 초기 페르소나 생성
            empathy_card = state.get("empathy_card", {}).get("content", "")
            reflection_card = state.get("reflection_card", {}).get("content", "")
            
            persona = self.create_initial_persona(empathy_card, reflection_card)
            
            state["persona"] = {
                "depth": persona.depth,
                "summary": persona.summary,
                "characteristics": persona.characteristics,
                "needs": persona.needs,
                "growth_direction": persona.growth_direction
            }
            
        elif routing_type == "ritual":
            # 페르소나 업데이트
            current_persona_dict = state.get("persona", {})
            if current_persona_dict:
                current_persona = Persona(**current_persona_dict)
                
                diary_entry = state.get("diary_entry", "")
                selected_mood = state.get("selected_mood", "")
                
                updated_persona = self.update_persona(
                    current_persona,
                    diary_entry,
                    selected_mood
                )
                
                state["persona"] = {
                    "depth": updated_persona.depth,
                    "summary": updated_persona.summary,
                    "characteristics": updated_persona.characteristics,
                    "needs": updated_persona.needs,
                    "growth_direction": updated_persona.growth_direction
                }
        
        state["persona_completed"] = True
        return state