"""
캘린더 기능 스키마
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import date


class DateRitualRequest(BaseModel):
    """날짜별 리츄얼 수정 요청"""
    daily_ritual: Optional[Dict[str, Any]] = Field(None, description="일일 리츄얼 수정 데이터")
    meari_ritual: Optional[Dict[str, Any]] = Field(None, description="메아리 리츄얼 수정 데이터")
    allow_completed_edit: bool = Field(False, description="완료된 리츄얼 수정 허용")
    
    class Config:
        json_schema_extra = {
            "example": {
                "daily_ritual": {
                    "title": "수정된 리츄얼 제목",
                    "description": "수정된 설명",
                    "user_note": "오늘의 메모",
                    "user_mood": "good"
                },
                "meari_ritual": {
                    "diary_entry": "오늘의 일기 수정...",
                    "selected_mood": "neutral"
                },
                "allow_completed_edit": False
            }
        }


class DateRitualResponse(BaseModel):
    """날짜별 리츄얼 응답"""
    date: date
    daily_ritual: Optional[Dict[str, Any]] = None
    meari_ritual: Optional[Dict[str, Any]] = None
    has_activity: bool = Field(False, description="활동 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-08-20",
                "daily_ritual": {
                    "id": 1,
                    "title": "10분 명상",
                    "description": "아침 명상하기",
                    "is_completed": True,
                    "user_mood": "good",
                    "can_edit": False
                },
                "meari_ritual": {
                    "id": 1,
                    "diary_entry": "오늘의 일기...",
                    "selected_mood": "neutral",
                    "can_edit": True
                },
                "has_activity": True
            }
        }


class MonthlyOverviewResponse(BaseModel):
    """월간 개요 응답"""
    year: int
    month: int
    days: List[Dict[str, Any]] = Field(default_factory=list, description="날짜별 데이터")
    statistics: Dict[str, Any] = Field(description="월간 통계")
    
    class Config:
        json_schema_extra = {
            "example": {
                "year": 2025,
                "month": 8,
                "days": [
                    {
                        "date": "2025-08-01",
                        "has_daily_ritual": True,
                        "daily_completed": True,
                        "has_meari_ritual": False,
                        "mood": "good",
                        "activity_count": 1
                    },
                    {
                        "date": "2025-08-02",
                        "has_daily_ritual": True,
                        "daily_completed": False,
                        "has_meari_ritual": True,
                        "mood": "neutral",
                        "activity_count": 2
                    }
                ],
                "statistics": {
                    "total_days": 31,
                    "active_days": 25,
                    "daily_rituals_completed": 20,
                    "meari_rituals_count": 15,
                    "activity_rate": 80.6,
                    "mood_distribution": {
                        "good": 15,
                        "neutral": 8,
                        "bad": 2
                    }
                }
            }
        }