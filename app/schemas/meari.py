from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID


# ========== 요청 스키마 ==========

class MeariSessionRequest(BaseModel):
    """최초 세션 생성 요청"""
    selected_tag_id: int = Field(
        ..., 
        description="선택된 중분류 태그 ID (1개)",
        ge=2,  # 최소 2 (첫 번째 중분류)
        le=12  # 최대 12 (마지막 중분류)
    )
    user_context: Optional[str] = Field(
        None,
        description="사용자가 입력한 구체적인 고민/상황",
        max_length=500
    )
    user_id: Optional[UUID] = Field(
        None,
        description="사용자 ID (선택사항)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "selected_tag_id": 2,
                "user_context": "매일 야근하고 주말에도 일해야 해서 너무 지쳐있어요. 회사를 그만두고 싶은데 다음 직장을 구할 수 있을지 불안합니다.",
                "user_id": None
            }
        }
    )


class GrowthContentRequest(BaseModel):
    """성장 콘텐츠 생성 요청"""
    context: Literal["initial", "ritual"] = Field(
        ...,
        description="컨텍스트 구분 (initial: 첫 방문, ritual: 리츄얼 후)"
    )
    previous_policy_ids: List[str] = Field(
        default_factory=list,
        description="이미 본 정책 ID 리스트 (중복 방지용)"
    )
    user_id: Optional[UUID] = Field(
        None,
        description="사용자 ID"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "context": "initial",
                "previous_policy_ids": ["POL001", "POL002"],
                "user_id": None
            }
        }
    )


class RitualRequest(BaseModel):
    """리츄얼 기록 요청"""
    diary_entry: str = Field(
        ...,
        description="사용자가 작성한 일기",
        min_length=1,
        max_length=1000
    )
    selected_mood: str = Field(
        ...,
        description="선택한 기분",
        example="hopeful"
    )
    growth_contents_viewed: List[str] = Field(
        default_factory=list,
        description="본 성장 콘텐츠 ID 리스트"
    )
    user_id: Optional[UUID] = Field(
        None,
        description="사용자 ID"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "diary_entry": "오늘은 추천받은 명상을 시도해봤어요. 생각보다 마음이 편안해졌습니다.",
                "selected_mood": "hopeful",
                "growth_contents_viewed": ["card_001", "card_002"],
                "user_id": None
            }
        }
    )


# ========== 응답 스키마 ==========

class EmpathyCard(BaseModel):
    """공감 카드"""
    type: Literal["empathy"] = "empathy"
    title: str = "당신의 마음을 이해해요"
    content: str = Field(..., description="AI가 생성한 공감 메시지")
    quotes_used: List[Dict[str, str]] = Field(..., description="사용된 인용문 리스트")
    emotion_keywords: List[str] = Field(default_factory=list, description="감정 키워드")


class StructuredInsights(BaseModel):
    """구조화된 통찰"""
    problem: str
    causes: List[str]
    solutions: List[str]
    supporters: List[str]
    peers: List[str]


class ReflectionCard(BaseModel):
    """성찰 카드"""
    type: Literal["reflection"] = "reflection"
    title: str = "당신은 혼자가 아니에요"
    content: str = Field(..., description="구조화된 성찰 메시지")
    insights: StructuredInsights
    key_message: str


class InformationCard(BaseModel):
    """정보 카드"""
    type: Literal["information"] = "information"
    title: str
    search_query: str = Field(..., description="검색 쿼리")
    summary: str = Field(..., description="정보 요약")
    sources: List[str] = Field(default_factory=list)


class ExperienceCard(BaseModel):
    """경험 카드"""
    type: Literal["experience"] = "experience"
    title: str
    activity: str = Field(..., description="추천 활동")
    duration: str = "10분 이내"
    difficulty: Literal["쉬움", "보통", "어려움"] = "쉬움"


class SupportCard(BaseModel):
    """지원 카드"""
    type: Literal["support"] = "support"
    title: str
    policy_name: str
    description: str
    organization: str
    application_url: Optional[str] = None


class PersonaData(BaseModel):
    """페르소나 데이터"""
    depth: Literal["surface", "understanding", "insight", "deep_insight", "wisdom"]
    depth_label: str
    summary: str
    characteristics: List[str]
    needs: List[str]
    growth_direction: str


class TreeStatus(BaseModel):
    """마음나무 상태"""
    stage: Literal["seed", "sprouting", "growing", "blooming", "full_bloom"]
    stage_label: str
    progress: int = Field(..., ge=0, le=28)
    next_milestone: Optional[int]
    percentage: float


class MeariSessionResponse(BaseModel):
    """최초 세션 응답"""
    status: Literal["success", "error"] = "success"
    session_type: Literal["initial"] = "initial"
    timestamp: datetime
    session_id: UUID
    cards: Dict[str, Any] = Field(
        ...,
        description="공감/성찰 카드"
    )
    persona: PersonaData
    next_action: str = "growth_content"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "session_type": "initial",
                "timestamp": "2024-01-01T00:00:00",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "cards": {
                    "empathy": "...",
                    "reflection": "..."
                },
                "persona": "...",
                "next_action": "growth_content"
            }
        }
    )


class GrowthContentResponse(BaseModel):
    """성장 콘텐츠 응답"""
    status: Literal["success", "error"] = "success"
    content_type: Literal["growth"] = "growth"
    timestamp: datetime
    cards: Dict[str, Any] = Field(
        ...,
        description="3종 성장 카드 (information, experience, support)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "content_type": "growth",
                "timestamp": "2024-01-01T00:00:00",
                "cards": {
                    "information": "...",
                    "experience": "...", 
                    "support": "..."
                }
            }
        }
    )


class RitualResponse(BaseModel):
    """리츄얼 응답"""
    status: Literal["success", "error"] = "success"
    action: Literal["ritual_recorded"] = "ritual_recorded"
    timestamp: datetime
    ritual_id: int
    persona: Dict[str, Any] = Field(
        ...,
        description="업데이트된 페르소나 정보"
    )
    tree: TreeStatus
    message: str = Field(
        ...,
        description="격려 메시지"
    )
    next_growth_content: Optional[Dict[str, Any]] = Field(
        None,
        description="다음 성장 콘텐츠 (선택사항)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "action": "ritual_recorded",
                "timestamp": "2024-01-01T00:00:00",
                "ritual_id": 1,
                "persona": {
                    "updated": True,
                    "depth": "understanding",
                    "summary": "..."
                },
                "tree": {
                    "stage": "sprouting",
                    "stage_label": "새싹",
                    "progress": 7,
                    "next_milestone": 14,
                    "percentage": 25.0
                },
                "message": "7일째 함께하고 있어요.",
                "next_growth_content": None
            }
        }
    )


# ========== 에러 응답 ==========

class ErrorResponse(BaseModel):
    """에러 응답"""
    status: Literal["error"] = "error"
    error_code: str
    message: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)