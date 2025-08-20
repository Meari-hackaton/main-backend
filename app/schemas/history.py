"""
활동 이력 및 통합 조회 스키마
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime


class DayDetailResponse(BaseModel):
    """특정 날짜 상세 응답"""
    date: date
    daily_ritual: Optional[Dict[str, Any]] = Field(None, description="일일 리츄얼")
    meari_ritual: Optional[Dict[str, Any]] = Field(None, description="메아리 일기")
    sessions: List[Dict[str, Any]] = Field(default_factory=list, description="메아리 세션 목록")
    generated_cards: List[Dict[str, Any]] = Field(default_factory=list, description="생성된 카드 목록")
    heart_tree_level: int = Field(0, description="마음나무 레벨")
    
    class Config:
        schema_extra = {
            "example": {
                "date": "2025-08-20",
                "daily_ritual": {
                    "id": 1,
                    "title": "10분 명상",
                    "is_completed": True,
                    "user_mood": "good"
                },
                "meari_ritual": {
                    "id": 1,
                    "diary_entry": "오늘의 일기...",
                    "selected_mood": "neutral"
                },
                "sessions": [
                    {
                        "id": "uuid",
                        "selected_tag_ids": [1, 4],
                        "created_at": "2025-08-20T10:00:00"
                    }
                ],
                "generated_cards": [
                    {
                        "card_type": "empathy",
                        "content": {}
                    }
                ],
                "heart_tree_level": 15
            }
        }


class SessionHistoryResponse(BaseModel):
    """세션 이력 응답"""
    total: int
    page: int
    limit: int
    sessions: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "total": 50,
                "page": 1,
                "limit": 20,
                "sessions": [
                    {
                        "id": "uuid",
                        "created_at": "2025-08-20T10:00:00",
                        "selected_tag_ids": [1, 4],
                        "card_count": 5
                    }
                ]
            }
        }


class CardSearchRequest(BaseModel):
    """카드 검색 요청"""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    card_type: Optional[str] = Field(None, description="empathy, reflection, growth")
    sub_type: Optional[str] = Field(None, description="information, experience, support")
    keyword: Optional[str] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class CardSearchResponse(BaseModel):
    """카드 검색 응답"""
    total: int
    page: int
    limit: int
    cards: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "limit": 20,
                "cards": [
                    {
                        "id": 1,
                        "session_id": "uuid",
                        "card_type": "growth",
                        "sub_type": "information",
                        "content": {},
                        "created_at": "2025-08-20T10:00:00"
                    }
                ]
            }
        }


class PersonaEvolutionResponse(BaseModel):
    """페르소나 진화 응답"""
    current: Optional[Dict[str, Any]] = Field(None, description="현재 페르소나")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="페르소나 이력")
    
    class Config:
        schema_extra = {
            "example": {
                "current": {
                    "depth": "growing",
                    "summary": "현재 페르소나 설명...",
                    "characteristics": ["특징1", "특징2"],
                    "needs": ["니즈1", "니즈2"],
                    "growth_direction": "성장 방향..."
                },
                "history": [
                    {
                        "id": 1,
                        "date": "2025-08-01",
                        "event_type": "initial",
                        "depth": "surface",
                        "summary": "초기 페르소나..."
                    }
                ]
            }
        }


class RitualStatsResponse(BaseModel):
    """리츄얼 통계 응답"""
    monthly: Dict[str, Any] = Field(description="월간 통계")
    weekly: List[Dict[str, Any]] = Field(default_factory=list, description="주간 통계")
    
    class Config:
        schema_extra = {
            "example": {
                "monthly": {
                    "year": 2025,
                    "month": 8,
                    "total_days": 31,
                    "daily_rituals_completed": 20,
                    "meari_rituals_completed": 15,
                    "total_completed": 35,
                    "completion_rate": 80.5,
                    "mood_distribution": {
                        "good": 15,
                        "neutral": 10,
                        "bad": 5
                    }
                },
                "weekly": [
                    {
                        "week_start": "2025-08-19",
                        "week_end": "2025-08-25",
                        "completed_days": 5,
                        "completion_rate": 71.4
                    }
                ]
            }
        }