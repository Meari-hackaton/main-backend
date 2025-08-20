"""
캘린더 기능 확장 API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, date, timedelta
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.daily import DailyRitual
from app.models.checkin import Ritual
from app.schemas.calendar import (
    DateRitualRequest,
    DateRitualResponse,
    MonthlyOverviewResponse
)

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"]
)


@router.get(
    "/date/{target_date}/ritual",
    response_model=DateRitualResponse,
    summary="특정 날짜 리츄얼 조회",
    description="특정 날짜의 일일 리츄얼과 메아리 리츄얼을 조회합니다"
)
async def get_date_ritual(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DateRitualResponse:
    """특정 날짜의 리츄얼 조회"""
    
    user_id = current_user.id
    
    # DailyRitual 조회
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date == target_date
        )
    )
    result = await db.execute(stmt)
    daily_ritual = result.scalar_one_or_none()
    
    # Ritual (메아리) 조회
    stmt = select(Ritual).where(
        and_(
            Ritual.user_id == user_id,
            Ritual.checkin_date == target_date
        )
    )
    result = await db.execute(stmt)
    meari_ritual = result.scalar_one_or_none()
    
    return DateRitualResponse(
        date=target_date,
        daily_ritual={
            "id": daily_ritual.id,
            "title": daily_ritual.ritual_title,
            "description": daily_ritual.ritual_description,
            "type": daily_ritual.ritual_type,
            "duration_minutes": daily_ritual.duration_minutes,
            "is_completed": daily_ritual.is_completed,
            "completed_at": daily_ritual.completed_at.isoformat() if daily_ritual.completed_at else None,
            "user_mood": daily_ritual.user_mood,
            "user_note": daily_ritual.user_note,
            "difficulty_rating": daily_ritual.difficulty_rating,
            "can_edit": not daily_ritual.is_completed  # 완료되지 않은 경우만 수정 가능
        } if daily_ritual else None,
        meari_ritual={
            "id": meari_ritual.id,
            "ritual_sequence": meari_ritual.ritual_sequence,
            "diary_entry": meari_ritual.diary_entry,
            "selected_mood": meari_ritual.selected_mood,
            "ritual_completed": meari_ritual.ritual_completed,
            "can_edit": True  # 메아리 일기는 항상 수정 가능
        } if meari_ritual else None,
        has_activity=bool(daily_ritual or meari_ritual)
    )


@router.put(
    "/date/{target_date}/ritual",
    response_model=DateRitualResponse,
    summary="특정 날짜 리츄얼 수정",
    description="특정 날짜의 리츄얼을 수정합니다"
)
async def update_date_ritual(
    target_date: date,
    request: DateRitualRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DateRitualResponse:
    """특정 날짜의 리츄얼 수정"""
    
    user_id = current_user.id
    
    # DailyRitual 수정
    if request.daily_ritual:
        stmt = select(DailyRitual).where(
            and_(
                DailyRitual.user_id == user_id,
                DailyRitual.date == target_date
            )
        )
        result = await db.execute(stmt)
        daily_ritual = result.scalar_one_or_none()
        
        if daily_ritual:
            if daily_ritual.is_completed and not request.allow_completed_edit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="완료된 리츄얼은 수정할 수 없습니다"
                )
            
            # 업데이트
            if request.daily_ritual.get("title"):
                daily_ritual.ritual_title = request.daily_ritual["title"]
            if request.daily_ritual.get("description"):
                daily_ritual.ritual_description = request.daily_ritual["description"]
            if request.daily_ritual.get("user_note") is not None:
                daily_ritual.user_note = request.daily_ritual["user_note"]
            if request.daily_ritual.get("user_mood"):
                daily_ritual.user_mood = request.daily_ritual["user_mood"]
        else:
            # 새로 생성
            daily_ritual = DailyRitual(
                user_id=user_id,
                date=target_date,
                ritual_title=request.daily_ritual.get("title", "새 리츄얼"),
                ritual_description=request.daily_ritual.get("description", ""),
                ritual_type=request.daily_ritual.get("type", "daily"),
                duration_minutes=request.daily_ritual.get("duration_minutes", 10)
            )
            db.add(daily_ritual)
    
    # Meari Ritual 수정
    if request.meari_ritual:
        stmt = select(Ritual).where(
            and_(
                Ritual.user_id == user_id,
                Ritual.checkin_date == target_date
            )
        )
        result = await db.execute(stmt)
        meari_ritual = result.scalar_one_or_none()
        
        if meari_ritual:
            # 업데이트
            if request.meari_ritual.get("diary_entry"):
                meari_ritual.diary_entry = request.meari_ritual["diary_entry"]
            if request.meari_ritual.get("selected_mood"):
                meari_ritual.selected_mood = request.meari_ritual["selected_mood"]
        else:
            # 새로 생성 (시퀀스 계산)
            stmt = select(func.count()).select_from(Ritual).where(
                Ritual.user_id == user_id
            )
            result = await db.execute(stmt)
            sequence = (result.scalar() or 0) + 1
            
            meari_ritual = Ritual(
                user_id=user_id,
                ritual_sequence=sequence,
                diary_entry=request.meari_ritual.get("diary_entry", ""),
                selected_mood=request.meari_ritual.get("selected_mood", "neutral"),
                ritual_completed=True,
                checkin_date=target_date
            )
            db.add(meari_ritual)
    
    await db.commit()
    
    # 수정된 데이터 다시 조회
    return await get_date_ritual(target_date, current_user, db)


@router.get(
    "/overview/{year}/{month}",
    response_model=MonthlyOverviewResponse,
    summary="월간 개요",
    description="특정 월의 전체 활동 개요를 조회합니다"
)
async def get_monthly_overview(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MonthlyOverviewResponse:
    """월간 활동 개요"""
    
    user_id = current_user.id
    
    # 해당 월의 날짜 범위
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # DailyRitual 조회
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date >= first_day,
            DailyRitual.date <= last_day
        )
    )
    result = await db.execute(stmt)
    daily_rituals = result.scalars().all()
    
    # Ritual (메아리) 조회
    stmt = select(Ritual).where(
        and_(
            Ritual.user_id == user_id,
            Ritual.checkin_date >= first_day,
            Ritual.checkin_date <= last_day
        )
    )
    result = await db.execute(stmt)
    meari_rituals = result.scalars().all()
    
    # 날짜별 데이터 구성
    date_map = {}
    
    # DailyRitual 매핑
    for dr in daily_rituals:
        date_str = dr.date.isoformat()
        if date_str not in date_map:
            date_map[date_str] = {
                "date": date_str,
                "has_daily_ritual": False,
                "daily_completed": False,
                "has_meari_ritual": False,
                "mood": None,
                "activity_count": 0
            }
        date_map[date_str]["has_daily_ritual"] = True
        date_map[date_str]["daily_completed"] = dr.is_completed
        date_map[date_str]["activity_count"] += 1
        if dr.user_mood:
            date_map[date_str]["mood"] = dr.user_mood
    
    # Meari Ritual 매핑
    for mr in meari_rituals:
        date_str = mr.checkin_date.isoformat()
        if date_str not in date_map:
            date_map[date_str] = {
                "date": date_str,
                "has_daily_ritual": False,
                "daily_completed": False,
                "has_meari_ritual": False,
                "mood": None,
                "activity_count": 0
            }
        date_map[date_str]["has_meari_ritual"] = True
        date_map[date_str]["activity_count"] += 1
        if mr.selected_mood and not date_map[date_str]["mood"]:
            date_map[date_str]["mood"] = mr.selected_mood
    
    # 통계 계산
    total_days = (last_day - first_day).days + 1
    active_days = len(date_map)
    completed_daily = sum(1 for d in date_map.values() if d["daily_completed"])
    meari_count = len(meari_rituals)
    
    # 기분 통계
    mood_stats = {}
    for data in date_map.values():
        if data["mood"]:
            mood_stats[data["mood"]] = mood_stats.get(data["mood"], 0) + 1
    
    return MonthlyOverviewResponse(
        year=year,
        month=month,
        days=list(date_map.values()),
        statistics={
            "total_days": total_days,
            "active_days": active_days,
            "daily_rituals_completed": completed_daily,
            "meari_rituals_count": meari_count,
            "activity_rate": (active_days / total_days * 100) if total_days > 0 else 0,
            "mood_distribution": mood_stats
        }
    )