"""
사용자 활동 이력 및 통합 조회 API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, String
from datetime import datetime, date, timedelta
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.daily import DailyRitual
from app.models.checkin import Ritual, HeartTree, AIPersonaHistory
from app.models.card import MeariSession, GeneratedCard
from app.schemas.history import (
    DayDetailResponse,
    SessionHistoryResponse,
    CardSearchRequest,
    CardSearchResponse,
    PersonaEvolutionResponse,
    RitualStatsResponse
)

router = APIRouter(
    prefix="/history",
    tags=["history"]
)


@router.get(
    "/day/{target_date}",
    response_model=DayDetailResponse,
    summary="특정 날짜 상세 조회",
    description="특정 날짜의 모든 활동 데이터를 조회합니다"
)
async def get_day_detail(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DayDetailResponse:
    """특정 날짜의 모든 활동 조회"""
    
    user_id = current_user.id
    
    # 1. DailyRitual 조회
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date == target_date
        )
    )
    result = await db.execute(stmt)
    daily_ritual = result.scalar_one_or_none()
    
    # 2. Ritual (메아리 일기) 조회
    stmt = select(Ritual).where(
        and_(
            Ritual.user_id == user_id,
            Ritual.checkin_date == target_date
        )
    )
    result = await db.execute(stmt)
    meari_ritual = result.scalar_one_or_none()
    
    # 3. 해당 날짜의 세션 조회
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    stmt = select(MeariSession).where(
        and_(
            MeariSession.user_id == user_id,
            MeariSession.created_at >= start_datetime,
            MeariSession.created_at <= end_datetime
        )
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    # 4. 해당 날짜의 카드 조회
    session_ids = [s.id for s in sessions]
    generated_cards = []
    
    if session_ids:
        stmt = select(GeneratedCard).where(
            GeneratedCard.session_id.in_(session_ids)
        ).order_by(GeneratedCard.created_at)
        result = await db.execute(stmt)
        cards = result.scalars().all()
        
        for card in cards:
            generated_cards.append({
                "id": card.id,
                "card_type": card.card_type,
                "sub_type": card.sub_type,
                "content": card.content,
                "growth_context": card.growth_context,
                "created_at": card.created_at.isoformat()
            })
    
    # 5. 마음나무 레벨 조회
    stmt = select(HeartTree).where(HeartTree.user_id == user_id)
    result = await db.execute(stmt)
    heart_tree = result.scalar_one_or_none()
    
    # 응답 구성
    return DayDetailResponse(
        date=target_date,
        daily_ritual={
            "id": daily_ritual.id,
            "title": daily_ritual.ritual_title,
            "description": daily_ritual.ritual_description,
            "is_completed": daily_ritual.is_completed,
            "user_mood": daily_ritual.user_mood,
            "user_note": daily_ritual.user_note,
            "completed_at": daily_ritual.completed_at.isoformat() if daily_ritual.completed_at else None
        } if daily_ritual else None,
        meari_ritual={
            "id": meari_ritual.id,
            "ritual_sequence": meari_ritual.ritual_sequence,
            "diary_entry": meari_ritual.diary_entry,
            "selected_mood": meari_ritual.selected_mood,
            "ritual_completed": meari_ritual.ritual_completed
        } if meari_ritual else None,
        sessions=[{
            "id": str(s.id),
            "selected_tag_ids": s.selected_tag_ids,
            "created_at": s.created_at.isoformat()
        } for s in sessions],
        generated_cards=generated_cards,
        heart_tree_level=heart_tree.growth_level if heart_tree else 0
    )


@router.get(
    "/sessions",
    response_model=SessionHistoryResponse,
    summary="세션 이력 조회",
    description="사용자의 메아리 세션 이력을 조회합니다"
)
async def get_session_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SessionHistoryResponse:
    """메아리 세션 이력 조회"""
    
    user_id = current_user.id
    offset = (page - 1) * limit
    
    # 전체 개수
    stmt = select(func.count()).select_from(MeariSession).where(
        MeariSession.user_id == user_id
    )
    result = await db.execute(stmt)
    total = result.scalar() or 0
    
    # 세션 목록
    stmt = select(MeariSession).where(
        MeariSession.user_id == user_id
    ).order_by(desc(MeariSession.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    # 각 세션의 카드 개수 조회
    session_data = []
    for session in sessions:
        stmt = select(func.count()).select_from(GeneratedCard).where(
            GeneratedCard.session_id == session.id
        )
        result = await db.execute(stmt)
        card_count = result.scalar() or 0
        
        session_data.append({
            "id": str(session.id),
            "created_at": session.created_at.isoformat(),
            "selected_tag_ids": session.selected_tag_ids,
            "card_count": card_count
        })
    
    return SessionHistoryResponse(
        total=total,
        page=page,
        limit=limit,
        sessions=session_data
    )


@router.post(
    "/cards/search",
    response_model=CardSearchResponse,
    summary="카드 검색",
    description="날짜, 타입, 키워드로 카드를 검색합니다"
)
async def search_cards(
    request: CardSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CardSearchResponse:
    """카드 검색"""
    
    user_id = current_user.id
    
    # 기본 쿼리
    stmt = select(GeneratedCard).where(
        GeneratedCard.user_id == user_id
    )
    
    # 날짜 필터
    if request.date_from:
        start_datetime = datetime.combine(request.date_from, datetime.min.time())
        stmt = stmt.where(GeneratedCard.created_at >= start_datetime)
    
    if request.date_to:
        end_datetime = datetime.combine(request.date_to, datetime.max.time())
        stmt = stmt.where(GeneratedCard.created_at <= end_datetime)
    
    # 카드 타입 필터
    if request.card_type:
        stmt = stmt.where(GeneratedCard.card_type == request.card_type)
    
    if request.sub_type:
        stmt = stmt.where(GeneratedCard.sub_type == request.sub_type)
    
    # 키워드 검색 (JSONB content 필드에서)
    if request.keyword:
        # PostgreSQL JSONB 텍스트 검색
        stmt = stmt.where(
            func.cast(GeneratedCard.content, String).ilike(f"%{request.keyword}%")
        )
    
    # 정렬 및 페이징
    offset = (request.page - 1) * request.limit
    stmt = stmt.order_by(desc(GeneratedCard.created_at)).offset(offset).limit(request.limit)
    
    result = await db.execute(stmt)
    cards = result.scalars().all()
    
    # 전체 개수 (필터 적용)
    count_stmt = select(func.count()).select_from(GeneratedCard).where(
        GeneratedCard.user_id == user_id
    )
    if request.date_from:
        count_stmt = count_stmt.where(GeneratedCard.created_at >= start_datetime)
    if request.date_to:
        count_stmt = count_stmt.where(GeneratedCard.created_at <= end_datetime)
    if request.card_type:
        count_stmt = count_stmt.where(GeneratedCard.card_type == request.card_type)
    if request.sub_type:
        count_stmt = count_stmt.where(GeneratedCard.sub_type == request.sub_type)
    
    result = await db.execute(count_stmt)
    total = result.scalar() or 0
    
    return CardSearchResponse(
        total=total,
        page=request.page,
        limit=request.limit,
        cards=[{
            "id": card.id,
            "session_id": str(card.session_id),
            "card_type": card.card_type,
            "sub_type": card.sub_type,
            "content": card.content,
            "growth_context": card.growth_context,
            "created_at": card.created_at.isoformat()
        } for card in cards]
    )


@router.get(
    "/persona/evolution",
    response_model=PersonaEvolutionResponse,
    summary="페르소나 진화 과정",
    description="사용자의 페르소나 진화 과정을 조회합니다"
)
async def get_persona_evolution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PersonaEvolutionResponse:
    """페르소나 진화 과정 조회"""
    
    user_id = current_user.id
    
    # 현재 페르소나
    stmt = select(AIPersonaHistory).where(
        and_(
            AIPersonaHistory.user_id == user_id,
            AIPersonaHistory.is_latest == True
        )
    )
    result = await db.execute(stmt)
    current_persona = result.scalar_one_or_none()
    
    # 페르소나 이력
    stmt = select(AIPersonaHistory).where(
        AIPersonaHistory.user_id == user_id
    ).order_by(AIPersonaHistory.event_date)
    
    result = await db.execute(stmt)
    history = result.scalars().all()
    
    return PersonaEvolutionResponse(
        current={
            "depth": current_persona.persona_data.get("depth", "surface"),
            "summary": current_persona.persona_data.get("summary", ""),
            "characteristics": current_persona.persona_data.get("characteristics", []),
            "needs": current_persona.persona_data.get("needs", []),
            "growth_direction": current_persona.persona_data.get("growth_direction", "")
        } if current_persona else None,
        history=[{
            "id": h.id,
            "date": h.event_date.isoformat(),
            "event_type": h.event_type,
            "depth": h.persona_data.get("depth", "surface"),
            "summary": h.persona_data.get("summary", "")
        } for h in history]
    )


@router.get(
    "/rituals/stats",
    response_model=RitualStatsResponse,
    summary="리츄얼 통계",
    description="월별, 주별 리츄얼 통계를 조회합니다"
)
async def get_ritual_stats(
    year: int = Query(None, description="연도 (기본값: 현재 연도)"),
    month: int = Query(None, ge=1, le=12, description="월 (기본값: 현재 월)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RitualStatsResponse:
    """리츄얼 통계 조회"""
    
    user_id = current_user.id
    today = date.today()
    
    if not year:
        year = today.year
    if not month:
        month = today.month
    
    # 월간 통계
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # DailyRitual 통계
    stmt = select(
        func.count(DailyRitual.id).label("total"),
        func.count(DailyRitual.id).filter(DailyRitual.is_completed == True).label("completed"),
        func.count(DailyRitual.user_mood).label("with_mood")
    ).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date >= first_day,
            DailyRitual.date <= last_day
        )
    )
    result = await db.execute(stmt)
    daily_stats = result.one()
    
    # Ritual (메아리) 통계
    stmt = select(
        func.count(Ritual.id).label("total"),
        func.count(Ritual.selected_mood).label("with_mood")
    ).where(
        and_(
            Ritual.user_id == user_id,
            Ritual.checkin_date >= first_day,
            Ritual.checkin_date <= last_day
        )
    )
    result = await db.execute(stmt)
    meari_stats = result.one()
    
    # 기분 분포
    mood_distribution = {}
    
    # DailyRitual 기분
    stmt = select(
        DailyRitual.user_mood,
        func.count(DailyRitual.id)
    ).where(
        and_(
            DailyRitual.user_id == user_id,
            DailyRitual.date >= first_day,
            DailyRitual.date <= last_day,
            DailyRitual.user_mood.isnot(None)
        )
    ).group_by(DailyRitual.user_mood)
    
    result = await db.execute(stmt)
    for mood, count in result:
        mood_distribution[mood] = mood_distribution.get(mood, 0) + count
    
    # Ritual 기분
    stmt = select(
        Ritual.selected_mood,
        func.count(Ritual.id)
    ).where(
        and_(
            Ritual.user_id == user_id,
            Ritual.checkin_date >= first_day,
            Ritual.checkin_date <= last_day,
            Ritual.selected_mood.isnot(None)
        )
    ).group_by(Ritual.selected_mood)
    
    result = await db.execute(stmt)
    for mood, count in result:
        mood_distribution[mood] = mood_distribution.get(mood, 0) + count
    
    # 주간 통계 (최근 4주)
    weekly_stats = []
    for week_offset in range(4):
        week_start = today - timedelta(days=today.weekday() + week_offset * 7)
        week_end = week_start + timedelta(days=6)
        
        # 주간 완료 일수
        stmt = select(func.count(DailyRitual.id)).where(
            and_(
                DailyRitual.user_id == user_id,
                DailyRitual.date >= week_start,
                DailyRitual.date <= week_end,
                DailyRitual.is_completed == True
            )
        )
        result = await db.execute(stmt)
        completed = result.scalar() or 0
        
        weekly_stats.append({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "completed_days": completed,
            "completion_rate": (completed / 7) * 100
        })
    
    total_days = (last_day - first_day).days + 1
    total_completed = daily_stats.completed + meari_stats.total
    
    return RitualStatsResponse(
        monthly={
            "year": year,
            "month": month,
            "total_days": total_days,
            "daily_rituals_completed": daily_stats.completed,
            "meari_rituals_completed": meari_stats.total,
            "total_completed": total_completed,
            "completion_rate": (total_completed / total_days) * 100 if total_days > 0 else 0,
            "mood_distribution": mood_distribution
        },
        weekly=weekly_stats
    )