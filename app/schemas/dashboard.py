from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from uuid import UUID


# ========== 요청 스키마 ==========

class DailyRitualCreateRequest(BaseModel):
    """일일 리츄얼 생성 요청"""
    title: str = Field(..., description="리츄얼 제목", max_length=200)
    description: str = Field(..., description="리츄얼 설명")
    type: str = Field(..., description="리츄얼 타입 (meditation, exercise, diary 등)")
    duration_minutes: int = Field(10, description="예상 소요 시간(분)", ge=1, le=60)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "10분 명상하기",
                "description": "조용한 곳에서 호흡에 집중하며 마음을 가라앉히세요",
                "type": "meditation",
                "duration_minutes": 10
            }
        }
    )


class DailyRitualUpdateRequest(BaseModel):
    """리츄얼 완료 시 업데이트 요청"""
    user_note: Optional[str] = Field(None, description="완료 후 메모")
    user_mood: Optional[str] = Field(None, description="완료 후 기분")
    difficulty_rating: Optional[int] = Field(None, description="난이도 평가 (1-5)", ge=1, le=5)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_note": "명상 후 마음이 많이 편안해졌어요",
                "user_mood": "calm",
                "difficulty_rating": 2
            }
        }
    )


# ========== 응답 스키마 ==========

class TreeStatus(BaseModel):
    """마음나무 상태"""
    level: int = Field(..., description="현재 레벨 (0-28+)")
    stage: Literal["seed", "sprouting", "growing", "blooming", "full_bloom"]
    stage_label: str = Field(..., description="단계 라벨")
    next_milestone: Optional[int] = Field(None, description="다음 목표 레벨")
    percentage: float = Field(..., description="진행률 (%)")


class Statistics(BaseModel):
    """활동 통계"""
    continuous_days: int = Field(..., description="연속 방문 일수")
    total_rituals: int = Field(..., description="총 완료한 리츄얼 수")
    practiced_rituals: int = Field(..., description="실천한 리츄얼 종류 수")
    monthly_completed: int = Field(..., description="이번 달 완료 일수")


class TodayRitual(BaseModel):
    """오늘의 리츄얼 요약"""
    id: Optional[int] = None
    title: Optional[str] = None
    is_completed: bool = False
    type: Optional[str] = None


class Notification(BaseModel):
    """알림 메시지"""
    type: Literal["ritual", "reminder", "achievement", "info"]
    message: str
    icon: str


class DashboardResponse(BaseModel):
    """대시보드 메인 응답"""
    tree: TreeStatus
    statistics: Statistics
    today_ritual: Optional[TodayRitual]
    notifications: List[Notification]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tree": {
                    "level": 7,
                    "stage": "sprouting",
                    "stage_label": "새싹",
                    "next_milestone": 14,
                    "percentage": 25.0
                },
                "statistics": {
                    "continuous_days": 7,
                    "total_rituals": 15,
                    "practiced_rituals": 8,
                    "monthly_completed": 7
                },
                "today_ritual": {
                    "id": 123,
                    "title": "10분 명상하기",
                    "is_completed": False,
                    "type": "meditation"
                },
                "notifications": [
                    {
                        "type": "reminder",
                        "message": "'10분 명상하기' 리츄얼이 기다리고 있어요",
                        "icon": "clock"
                    }
                ]
            }
        }
    )


class DayData(BaseModel):
    """캘린더 일별 데이터"""
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    has_ritual: bool = Field(..., description="리츄얼 여부")
    is_completed: bool = Field(..., description="완료 여부")
    ritual_id: Optional[int] = None
    ritual_title: Optional[str] = None
    ritual_type: Optional[str] = None
    user_mood: Optional[str] = None


class CalendarSummary(BaseModel):
    """캘린더 월별 요약"""
    total_days: int
    completed_days: int
    completion_rate: float
    current_streak: int


class CalendarResponse(BaseModel):
    """캘린더 응답"""
    year: int
    month: int
    days: List[DayData]
    summary: CalendarSummary
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "year": 2024,
                "month": 5,
                "days": [
                    {
                        "date": "2024-05-01",
                        "has_ritual": True,
                        "is_completed": True,
                        "ritual_id": 1,
                        "ritual_title": "아침 요가",
                        "ritual_type": "exercise",
                        "user_mood": "energetic"
                    }
                ],
                "summary": {
                    "total_days": 31,
                    "completed_days": 15,
                    "completion_rate": 48.4,
                    "current_streak": 7
                }
            }
        }
    )


class DailyRitualResponse(BaseModel):
    """일일 리츄얼 상세 응답"""
    id: int
    date: date
    title: str
    description: str
    type: str
    duration_minutes: int
    is_completed: bool
    completed_at: Optional[datetime] = None
    user_note: Optional[str] = None
    user_mood: Optional[str] = None
    difficulty_rating: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "date": "2024-05-01",
                "title": "10분 명상하기",
                "description": "조용한 곳에서 호흡에 집중하며 마음을 가라앉히세요",
                "type": "meditation",
                "duration_minutes": 10,
                "is_completed": True,
                "completed_at": "2024-05-01T09:30:00",
                "user_note": "명상 후 마음이 편안해졌어요",
                "user_mood": "calm",
                "difficulty_rating": 2
            }
        }
    )


class StreakResponse(BaseModel):
    """연속 기록 응답"""
    current_streak: int = Field(..., description="현재 연속 일수")
    longest_streak: int = Field(..., description="최장 연속 일수")
    total_days_active: int = Field(..., description="총 활동 일수")
    total_rituals_completed: int = Field(..., description="총 완료 리츄얼")
    total_rituals_created: int = Field(..., description="총 생성 리츄얼")
    last_activity_date: Optional[date] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_streak": 7,
                "longest_streak": 21,
                "total_days_active": 45,
                "total_rituals_completed": 50,
                "total_rituals_created": 52,
                "last_activity_date": "2024-05-01"
            }
        }
    )