"""
대시보드 및 통계 API 엔드포인트
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, date, timedelta
import calendar

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.daily import DailyRitual, UserStreak
from app.models.checkin import HeartTree, Ritual
from app.schemas.dashboard import (
    DashboardResponse,
    CalendarResponse,
    DailyRitualResponse,
    DailyRitualCreateRequest,
    DailyRitualUpdateRequest,
    StreakResponse
)

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)

# 테스트용 더미 사용자 ID
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


@router.get(
    "/test",
    response_model=DashboardResponse,
    summary="대시보드 테스트 (인증 없음)",
    description="테스트용 대시보드 데이터 조회"
)
async def get_dashboard_test(
    db: AsyncSession = Depends(get_db)
) -> DashboardResponse:
    """테스트용 대시보드 데이터"""
    
    user_id = TEST_USER_ID
    today = date.today()
    
    # 1. 마음나무 상태
    stmt = select(HeartTree).where(HeartTree.user_id == user_id)
    result = await db.execute(stmt)
    heart_tree = result.scalar_one_or_none()
    
    tree_level = heart_tree.growth_level if heart_tree else 1  # 기본값 1
    tree_stage = _get_tree_stage(tree_level)
    
    # 2. 연속 기록 조회 또는 생성
    stmt = select(UserStreak).where(UserStreak.user_id == user_id)
    result = await db.execute(stmt)
    streak = result.scalar_one_or_none()
    
    if not streak:
        # 테스트용 기본값
        streak = UserStreak(
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
            total_days_active=1,
            total_rituals_completed=0,
            total_rituals_created=0
        )
    
    # 3. 오늘의 리츄얼
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date == today
        )
    )
    result = await db.execute(stmt)
    today_ritual = result.scalar_one_or_none()
    
    # 4. 이번 달 완료 일수
    first_day = date(today.year, today.month, 1)
    stmt = select(func.count(DailyRitual.id)).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date >= first_day,
            DailyRitual.is_completed == True
        )
    )
    result = await db.execute(stmt)
    monthly_completed = result.scalar() or 0
    
    # 5. 알림 메시지 생성
    notifications = []
    if not today_ritual:
        notifications.append({
            "type": "ritual",
            "message": "오늘의 리츄얼을 확인해보세요",
            "icon": "ritual"
        })
    
    from app.schemas.dashboard import TreeStatus, Statistics, TodayRitual, Notification
    
    # notifications를 Notification 모델로 변환
    notification_objects = [
        Notification(**notif) for notif in notifications
    ]
    
    return DashboardResponse(
        tree=TreeStatus(
            level=tree_level,
            stage=tree_stage["stage"],
            stage_label=tree_stage["label"],
            next_milestone=tree_stage["next_milestone"],
            percentage=min(tree_level / 28 * 100, 100)
        ),
        statistics=Statistics(
            continuous_days=streak.current_streak or 0,
            total_rituals=streak.total_rituals_completed or 0,
            practiced_rituals=getattr(streak, 'total_rituals_created', 0),
            monthly_completed=int(monthly_completed)
        ),
        today_ritual=TodayRitual(
            id=today_ritual.id if today_ritual else None,
            title=today_ritual.ritual_title if today_ritual else "오늘의 리츄얼 받기",
            is_completed=today_ritual.is_completed if today_ritual else False,
            type=today_ritual.ritual_type if today_ritual else "growth_experience"
        ),
        notifications=notification_objects
    )


@router.get(
    "/",
    response_model=DashboardResponse,
    summary="대시보드 메인",
    description="마음나무 상태와 활동 통계를 조회합니다"
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DashboardResponse:
    """대시보드 메인 데이터"""
    
    user_id = current_user.id
    today = date.today()
    
    # 1. 마음나무 상태
    stmt = select(HeartTree).where(HeartTree.user_id == user_id)
    result = await db.execute(stmt)
    heart_tree = result.scalar_one_or_none()
    
    tree_level = heart_tree.growth_level if heart_tree else 0
    tree_stage = _get_tree_stage(tree_level)
    
    # 2. 연속 기록 조회 또는 생성
    stmt = select(UserStreak).where(UserStreak.user_id == user_id)
    result = await db.execute(stmt)
    streak = result.scalar_one_or_none()
    
    if not streak:
        streak = UserStreak(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            total_days_active=0,
            total_rituals_completed=0,
            total_rituals_created=0
        )
        db.add(streak)
        await db.flush()
    
    # 3. 오늘의 리츄얼
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date == today
        )
    )
    result = await db.execute(stmt)
    today_ritual = result.scalar_one_or_none()
    
    # 4. 이번 달 완료 일수
    first_day = date(today.year, today.month, 1)
    stmt = select(func.count(DailyRitual.id)).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date >= first_day,
            DailyRitual.is_completed == True
        )
    )
    result = await db.execute(stmt)
    monthly_completed = result.scalar() or 0
    
    # 5. 알림 메시지 생성
    notifications = []
    if not today_ritual:
        notifications.append({
            "type": "ritual",
            "message": "오늘의 리츄얼을 확인해보세요",
            "icon": "ritual"
        })
    elif not today_ritual.is_completed:
        notifications.append({
            "type": "reminder",
            "message": f"'{today_ritual.ritual_title}' 리츄얼이 기다리고 있어요",
            "icon": "clock"
        })
    
    if streak.current_streak > 0 and streak.current_streak % 7 == 0:
        notifications.append({
            "type": "achievement",
            "message": f"{streak.current_streak}일 연속 달성!",
            "icon": "trophy"
        })
    
    from app.schemas.dashboard import TreeStatus, Statistics, TodayRitual, Notification
    
    # notifications를 Notification 모델로 변환
    notification_objects = [
        Notification(**notif) for notif in notifications
    ]
    
    return DashboardResponse(
        tree=TreeStatus(
            level=tree_level,
            stage=tree_stage["stage"],
            stage_label=tree_stage["label"],
            next_milestone=tree_stage["next_milestone"],
            percentage=min(tree_level / 28 * 100, 100)
        ),
        statistics=Statistics(
            continuous_days=streak.current_streak,
            total_rituals=streak.total_rituals_completed,
            practiced_rituals=getattr(streak, 'total_rituals_created', 0),
            monthly_completed=int(monthly_completed)
        ),
        today_ritual=TodayRitual(
            id=today_ritual.id if today_ritual else None,
            title=today_ritual.ritual_title if today_ritual else "오늘의 리츄얼 받기",
            is_completed=today_ritual.is_completed if today_ritual else False,
            type=today_ritual.ritual_type if today_ritual else "growth_experience"
        ),
        notifications=notification_objects
    )


@router.get(
    "/calendar",
    response_model=CalendarResponse,
    summary="캘린더 데이터",
    description="월별 리츄얼 완료 현황을 조회합니다"
)
async def get_calendar(
    year: int = Query(..., description="연도"),
    month: int = Query(..., ge=1, le=12, description="월"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CalendarResponse:
    """월별 캘린더 데이터"""
    
    user_id = current_user.id
    
    # 해당 월의 첫날과 마지막날
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    # 해당 월의 모든 리츄얼 조회
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date >= first_day,
            DailyRitual.date <= last_day
        )
    ).order_by(DailyRitual.date)
    
    result = await db.execute(stmt)
    rituals = result.scalars().all()
    
    # 날짜별 데이터 구성
    daily_data = {}
    for ritual in rituals:
        date_str = ritual.date.isoformat()
        daily_data[date_str] = {
            "date": date_str,
            "has_ritual": True,
            "is_completed": ritual.is_completed,
            "ritual_id": ritual.id,
            "ritual_title": ritual.ritual_title,
            "ritual_type": ritual.ritual_type,
            "user_mood": ritual.user_mood if ritual.is_completed else None
        }
    
    # 빈 날짜 채우기
    current_date = first_day
    while current_date <= last_day:
        date_str = current_date.isoformat()
        if date_str not in daily_data:
            daily_data[date_str] = {
                "date": date_str,
                "has_ritual": False,
                "is_completed": False
            }
        current_date += timedelta(days=1)
    
    # 정렬된 리스트로 변환
    days = sorted(daily_data.values(), key=lambda x: x["date"])
    
    # 연속 기록 계산
    completed_dates = [d["date"] for d in days if d["is_completed"]]
    current_streak = _calculate_current_streak(completed_dates)
    
    return CalendarResponse(
        year=year,
        month=month,
        days=days,
        summary={
            "total_days": len(days),
            "completed_days": len([d for d in days if d["is_completed"]]),
            "completion_rate": len([d for d in days if d["is_completed"]]) / len(days) * 100 if days else 0,
            "current_streak": current_streak
        }
    )


@router.get(
    "/rituals/today",
    response_model=DailyRitualResponse,
    summary="오늘의 리츄얼",
    description="오늘 할당된 리츄얼을 조회합니다"
)
async def get_today_ritual(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DailyRitualResponse:
    """오늘의 리츄얼 조회"""
    
    today = date.today()
    
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == current_user.id,
            DailyRitual.date == today
        )
    )
    result = await db.execute(stmt)
    ritual = result.scalar_one_or_none()
    
    if not ritual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="오늘의 리츄얼이 없습니다"
        )
    
    return DailyRitualResponse(
        id=ritual.id,
        date=ritual.date,
        title=ritual.ritual_title,
        description=ritual.ritual_description,
        type=ritual.ritual_type,
        duration_minutes=ritual.duration_minutes,
        is_completed=ritual.is_completed,
        completed_at=ritual.completed_at,
        user_note=ritual.user_note,
        user_mood=ritual.user_mood,
        difficulty_rating=ritual.difficulty_rating
    )


@router.post(
    "/rituals",
    response_model=DailyRitualResponse,
    status_code=status.HTTP_201_CREATED,
    summary="리츄얼 생성",
    description="오늘의 리츄얼을 생성합니다"
)
async def create_daily_ritual(
    request: DailyRitualCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DailyRitualResponse:
    """일일 리츄얼 생성"""
    
    today = date.today()
    
    # 오늘 이미 리츄얼이 있는지 확인
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == current_user.id,
            DailyRitual.date == today
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="오늘의 리츄얼이 이미 존재합니다"
        )
    
    # 리츄얼 생성
    ritual = DailyRitual(
        user_id=current_user.id,
        date=today,
        ritual_title=request.title,
        ritual_description=request.description,
        ritual_type=request.type,
        duration_minutes=request.duration_minutes
    )
    db.add(ritual)
    
    # UserStreak 업데이트
    stmt = select(UserStreak).where(UserStreak.user_id == current_user.id)
    result = await db.execute(stmt)
    streak = result.scalar_one_or_none()
    
    if streak:
        streak.total_rituals_created += 1
    else:
        streak = UserStreak(
            user_id=current_user.id,
            total_rituals_created=1
        )
        db.add(streak)
    
    await db.commit()
    await db.refresh(ritual)
    
    return DailyRitualResponse(
        id=ritual.id,
        date=ritual.date,
        title=ritual.ritual_title,
        description=ritual.ritual_description,
        type=ritual.ritual_type,
        duration_minutes=ritual.duration_minutes,
        is_completed=False
    )


@router.patch(
    "/rituals/{ritual_id}/complete",
    response_model=DailyRitualResponse,
    summary="리츄얼 완료",
    description="리츄얼을 완료 처리합니다"
)
async def complete_ritual(
    ritual_id: int,
    request: DailyRitualUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DailyRitualResponse:
    """리츄얼 완료 처리"""
    
    # 리츄얼 조회
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.id == ritual_id,
            DailyRitual.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    ritual = result.scalar_one_or_none()
    
    if not ritual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리츄얼을 찾을 수 없습니다"
        )
    
    if ritual.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 완료된 리츄얼입니다"
        )
    
    # 완료 처리
    ritual.is_completed = True
    ritual.completed_at = datetime.utcnow()
    ritual.user_note = request.user_note
    ritual.user_mood = request.user_mood
    ritual.difficulty_rating = request.difficulty_rating
    
    # UserStreak 업데이트
    await _update_user_streak(current_user.id, db)
    
    # HeartTree 업데이트
    stmt = select(HeartTree).where(HeartTree.user_id == current_user.id)
    result = await db.execute(stmt)
    heart_tree = result.scalar_one_or_none()
    
    if heart_tree:
        heart_tree.growth_level += 1
        heart_tree.last_grew_at = datetime.utcnow()
    else:
        heart_tree = HeartTree(
            user_id=current_user.id,
            growth_level=1,
            last_grew_at=datetime.utcnow()
        )
        db.add(heart_tree)
    
    await db.commit()
    await db.refresh(ritual)
    
    return DailyRitualResponse(
        id=ritual.id,
        date=ritual.date,
        title=ritual.ritual_title,
        description=ritual.ritual_description,
        type=ritual.ritual_type,
        duration_minutes=ritual.duration_minutes,
        is_completed=ritual.is_completed,
        completed_at=ritual.completed_at,
        user_note=ritual.user_note,
        user_mood=ritual.user_mood,
        difficulty_rating=ritual.difficulty_rating
    )


@router.get(
    "/streak",
    response_model=StreakResponse,
    summary="연속 기록",
    description="사용자의 연속 활동 기록을 조회합니다"
)
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StreakResponse:
    """연속 기록 조회"""
    
    stmt = select(UserStreak).where(UserStreak.user_id == current_user.id)
    result = await db.execute(stmt)
    streak = result.scalar_one_or_none()
    
    if not streak:
        return StreakResponse(
            current_streak=0,
            longest_streak=0,
            total_days_active=0,
            total_rituals_completed=0,
            total_rituals_created=0
        )
    
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        total_days_active=streak.total_days_active,
        total_rituals_completed=streak.total_rituals_completed,
        total_rituals_created=streak.total_rituals_created,
        last_activity_date=streak.last_activity_date
    )


# ========== Helper Functions ==========

def _get_tree_stage(level: int) -> Dict[str, Any]:
    """마음나무 단계 계산"""
    if level <= 6:
        return {"stage": "seed", "label": "씨앗", "next_milestone": 7}
    elif level <= 13:
        return {"stage": "sprouting", "label": "새싹", "next_milestone": 14}
    elif level <= 20:
        return {"stage": "growing", "label": "성장", "next_milestone": 21}
    elif level <= 27:
        return {"stage": "blooming", "label": "개화", "next_milestone": 28}
    else:
        return {"stage": "full_bloom", "label": "만개", "next_milestone": None}


def _calculate_current_streak(completed_dates: List[str]) -> int:
    """현재 연속 일수 계산"""
    if not completed_dates:
        return 0
    
    # 날짜 문자열을 date 객체로 변환하고 정렬
    dates = sorted([date.fromisoformat(d) for d in completed_dates], reverse=True)
    
    # 오늘 또는 어제부터 시작해야 연속으로 인정
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    if dates[0] != today and dates[0] != yesterday:
        return 0
    
    streak = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i-1] - timedelta(days=1):
            streak += 1
        else:
            break
    
    return streak


async def _update_user_streak(user_id: str, db: AsyncSession):
    """UserStreak 업데이트"""
    
    stmt = select(UserStreak).where(UserStreak.user_id == user_id)
    result = await db.execute(stmt)
    streak = result.scalar_one_or_none()
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    if not streak:
        streak = UserStreak(
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
            total_days_active=1,
            total_rituals_completed=1,
            last_activity_date=today,
            last_ritual_date=today
        )
        db.add(streak)
    else:
        # 연속 기록 업데이트
        if streak.last_ritual_date == yesterday:
            streak.current_streak += 1
        elif streak.last_ritual_date != today:
            streak.current_streak = 1
        
        # 최장 기록 업데이트
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        
        # 통계 업데이트
        if streak.last_ritual_date != today:
            streak.total_days_active += 1
        
        streak.total_rituals_completed += 1
        streak.last_activity_date = today
        streak.last_ritual_date = today