"""
28일 챌린지 완주 관련 API 엔드포인트
"""
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.checkin import Ritual, AIPersonaHistory
from app.models.daily import DailyRitual
from app.models.card import GeneratedCard
from app.services.ai.completion_report import CompletionReportGenerator
from pydantic import BaseModel
import json

router = APIRouter()

class CompletionCheckResponse(BaseModel):
    is_completed: bool
    total_rituals: int
    days_completed: int
    message: str

class CompletionReportResponse(BaseModel):
    report: dict
    generated_at: datetime
    
@router.get(
    "/check",
    response_model=CompletionCheckResponse,
    summary="28일 완주 여부 확인"
)
async def check_completion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CompletionCheckResponse:
    """사용자의 28일 챌린지 완주 여부를 확인합니다."""
    
    # 완료된 리츄얼 개수 확인
    stmt = select(func.count(Ritual.id)).where(
        and_(
            Ritual.user_id == current_user.id,
            Ritual.ritual_completed == True
        )
    )
    result = await db.execute(stmt)
    ritual_count = result.scalar() or 0
    
    # DailyRitual 완료 개수도 포함
    stmt = select(func.count(DailyRitual.id)).where(
        and_(
            DailyRitual.user_id == current_user.id,
            DailyRitual.is_completed == True
        )
    )
    result = await db.execute(stmt)
    daily_ritual_count = result.scalar() or 0
    
    total_rituals = ritual_count + daily_ritual_count
    is_completed = total_rituals >= 28
    
    message = f"{'축하합니다! 28일 챌린지를 완주하셨습니다!' if is_completed else f'{28 - total_rituals}일 더 실천하면 완주입니다!'}"
    
    return CompletionCheckResponse(
        is_completed=is_completed,
        total_rituals=total_rituals,
        days_completed=total_rituals,
        message=message
    )

@router.get(
    "/report",
    response_model=CompletionReportResponse,
    summary="28일 완주 리포트 생성"
)
async def generate_completion_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CompletionReportResponse:
    """28일 챌린지 완주 시 AI가 생성하는 성장 리포트"""
    
    # 완주 여부 재확인
    check_result = await check_completion(current_user, db)
    if not check_result.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="아직 28일 챌린지를 완주하지 않았습니다."
        )
    
    # 모든 페르소나 히스토리 가져오기
    stmt = select(AIPersonaHistory).where(
        AIPersonaHistory.user_id == current_user.id
    ).order_by(AIPersonaHistory.created_at)
    result = await db.execute(stmt)
    persona_histories = result.scalars().all()
    
    # 모든 리츄얼 데이터 가져오기
    stmt = select(Ritual).where(
        and_(
            Ritual.user_id == current_user.id,
            Ritual.ritual_completed == True
        )
    ).order_by(Ritual.created_at)
    result = await db.execute(stmt)
    rituals = result.scalars().all()
    
    # DailyRitual 데이터도 가져오기
    stmt = select(DailyRitual).where(
        and_(
            DailyRitual.user_id == current_user.id,
            DailyRitual.is_completed == True
        )
    ).order_by(DailyRitual.date)
    result = await db.execute(stmt)
    daily_rituals = result.scalars().all()
    
    # 생성된 카드들 가져오기 (감정 분석용)
    stmt = select(GeneratedCard).where(
        GeneratedCard.user_id == current_user.id
    ).order_by(GeneratedCard.created_at)
    result = await db.execute(stmt)
    cards = result.scalars().all()
    
    # AI 리포트 생성
    generator = CompletionReportGenerator()
    report = await generator.generate_report(
        persona_histories=persona_histories,
        rituals=rituals,
        daily_rituals=daily_rituals,
        cards=cards,
        user_name=current_user.nickname or "당신"
    )
    
    return CompletionReportResponse(
        report=report,
        generated_at=datetime.now()
    )