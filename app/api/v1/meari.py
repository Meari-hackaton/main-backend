"""
메아리 API 엔드포인트
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.meari import (
    MeariSessionRequest,
    MeariSessionResponse,
    GrowthContentRequest,
    GrowthContentResponse,
    RitualRequest,
    RitualResponse,
    TreeStatus
)
from app.models.card import MeariSession, GeneratedCard
from app.models.checkin import AIPersonaHistory, Ritual, HeartTree
from app.models.history import UserContentHistory
from app.services.ai.workflow import MeariWorkflow

router = APIRouter(
    prefix="/meari",
    tags=["meari"]
)


@router.post(
    "/sessions",
    response_model=MeariSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메아리 세션 생성",
    description="태그 선택과 고민 입력으로 AI 카드와 페르소나를 생성합니다"
)
async def create_meari_session(
    request: MeariSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MeariSessionResponse:
    
    try:
        workflow = MeariWorkflow()
        
        workflow_request = {
            "request_type": "initial_session",
            "endpoint": "/api/meari-sessions",
            "tag_ids": [request.selected_tag_id],  # 배열로 전달
            "user_context": request.user_context or f"태그 {request.selected_tag_id}번 관련 고민"
        }
        
        # 동기 함수를 비동기로 실행
        import asyncio
        loop = asyncio.get_event_loop()
        workflow_result = await loop.run_in_executor(
            None,  # 기본 ThreadPoolExecutor 사용
            workflow.process_request,
            workflow_request
        )
        
        # 디버깅: 결과 확인
        print(f"워크플로우 결과 키: {list(workflow_result.keys())}")
        print(f"에러 여부: {'error' in workflow_result}")
        
        if "error" in workflow_result:
            print(f"워크플로우 에러: {workflow_result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=workflow_result.get("message", "워크플로우 처리 실패")
            )
        
        session_id = uuid.uuid4()
        user_id = current_user.id  # 인증된 사용자의 ID 사용
        
        session = MeariSession(
            id=session_id,
            user_id=user_id,
            selected_tag_ids=[request.selected_tag_id],
            created_at=datetime.utcnow()
        )
        db.add(session)
        
        cards_for_db = workflow_result.get("cards_for_db", [])
        for card_data in cards_for_db:
            card = GeneratedCard(
                session_id=session_id,
                user_id=user_id,  # 위에서 생성한 user_id 사용
                card_type=card_data.get("card_type"),
                sub_type=card_data.get("sub_type"),
                content=card_data.get("content"),
                source_ids=card_data.get("source_ids"),
                growth_context=card_data.get("growth_context", "initial")
            )
            db.add(card)
        
        persona_data = workflow_result.get("persona", {})
        if persona_data:  # user_id가 있으면 항상 페르소나 저장
            # SQLAlchemy 2.0 스타일로 변경
            from sqlalchemy import update
            stmt = update(AIPersonaHistory).where(
                AIPersonaHistory.user_id == user_id,
                AIPersonaHistory.is_latest == True
            ).values(is_latest=False)
            await db.execute(stmt)
            
            persona_history = AIPersonaHistory(
                user_id=user_id,
                persona_data=persona_data,
                event_type="initial",
                is_latest=True,
                event_date=datetime.utcnow().date()
            )
            db.add(persona_history)
        
        await db.commit()
        
        return MeariSessionResponse(
            status="success",
            session_type="initial",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            cards=workflow_result.get("cards", {}),
            persona=persona_data,
            next_action="growth_content"
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성 중 오류 발생: {str(e)}"
        )


@router.post(
    "/growth-contents",
    response_model=GrowthContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="성장 콘텐츠 생성",
    description="페르소나 기반으로 맞춤형 성장 콘텐츠를 생성합니다"
)
async def create_growth_contents(
    request: GrowthContentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GrowthContentResponse:
    
    try:
        # 세션 확인
        stmt = select(MeariSession).where(MeariSession.id == request.session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )
        
        # 인증된 사용자 ID 사용
        user_id = current_user.id
        
        # 최신 페르소나 가져오기
        persona_summary = request.persona_summary
        if not persona_summary and user_id:
            stmt = select(AIPersonaHistory).where(
                AIPersonaHistory.user_id == user_id,
                AIPersonaHistory.is_latest == True
            )
            result = await db.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona:
                persona_summary = persona.persona_data.get("summary", "")
        
        # 사용자가 이미 본 정책 ID 가져오기
        from app.models.history import UserContentHistory
        stmt = select(UserContentHistory.content_id).where(
            UserContentHistory.user_id == user_id,
            UserContentHistory.content_type == "policy"
        )
        result = await db.execute(stmt)
        viewed_policy_ids = [row[0] for row in result.fetchall()]
        
        # 요청에서 제공된 previous_policy_ids와 병합
        all_previous_policy_ids = list(set(request.previous_policy_ids + viewed_policy_ids))
        
        # 워크플로우 실행
        workflow = MeariWorkflow()
        
        workflow_request = {
            "request_type": "growth_content",
            "endpoint": "/api/growth-contents",
            "context": request.context,
            "session_id": str(request.session_id),
            "persona_summary": persona_summary,
            "previous_policy_ids": all_previous_policy_ids,  # 병합된 리스트 사용
            "user_id": str(user_id) if user_id else None
        }
        
        # 동기 함수를 비동기로 실행
        import asyncio
        loop = asyncio.get_event_loop()
        workflow_result = await loop.run_in_executor(
            None,  # 기본 ThreadPoolExecutor 사용
            workflow.process_request,
            workflow_request
        )
        workflow.close()
        
        # 카드 저장
        cards_for_db = workflow_result.get("cards_for_db", [])
        for card_data in cards_for_db:
            card = GeneratedCard(
                session_id=request.session_id,
                user_id=user_id,
                card_type=card_data.get("card_type"),
                sub_type=card_data.get("sub_type"),
                content=card_data.get("content"),
                source_ids=card_data.get("source_ids"),
                growth_context=card_data.get("growth_context", request.context)
            )
            db.add(card)
            
            # support 카드에서 정책 ID 추출하여 이력 저장
            if card_data.get("sub_type") == "support" and card_data.get("source_ids"):
                policy_ids = card_data["source_ids"].get("policies", [])
                for policy_id in policy_ids:
                    if policy_id:
                        # 중복 체크 - 이미 존재하는지 확인
                        stmt = select(UserContentHistory).where(
                            UserContentHistory.user_id == user_id,
                            UserContentHistory.content_type == "policy",
                            UserContentHistory.content_id == policy_id
                        )
                        result = await db.execute(stmt)
                        existing = result.scalar_one_or_none()
                        
                        if not existing:
                            history = UserContentHistory(
                                user_id=user_id,
                                content_type="policy",
                                content_id=policy_id
                            )
                            db.add(history)
        
        # Experience 카드를 DailyRitual로도 저장 (대시보드 연동)
        from app.models.daily import DailyRitual
        from datetime import date, timedelta
        
        experience_card = workflow_result.get("cards", {}).get("experience")
        if experience_card:
            today = date.today()
            
            # 오늘의 DailyRitual이 없으면 생성
            stmt = select(DailyRitual).where(
                DailyRitual.user_id == user_id,
                DailyRitual.date == today
            )
            result = await db.execute(stmt)
            existing_ritual = result.scalar_one_or_none()
            
            if not existing_ritual:
                daily_ritual = DailyRitual(
                    user_id=user_id,
                    date=today,
                    ritual_title=experience_card.get("ritual_name", "오늘의 리츄얼"),
                    ritual_description=experience_card.get("description", ""),
                    ritual_type="growth_experience",  # 성장 콘텐츠에서 온 것 표시
                    duration_minutes=10  # 기본값
                )
                
                # duration 파싱 시도
                duration_str = experience_card.get("duration", "10분")
                if "분" in duration_str:
                    try:
                        minutes = int(duration_str.replace("분", "").strip())
                        daily_ritual.duration_minutes = minutes
                    except:
                        pass
                
                db.add(daily_ritual)
        
        await db.commit()
        
        return GrowthContentResponse(
            status="success",
            content_type="growth",
            timestamp=datetime.utcnow(),
            cards=workflow_result.get("cards", {})
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"성장 콘텐츠 생성 중 오류 발생: {str(e)}"
        )


@router.post(
    "/rituals",
    response_model=RitualResponse,
    status_code=status.HTTP_201_CREATED,
    summary="리츄얼 기록",
    description="사용자의 일기와 기분을 기록하고 페르소나를 업데이트합니다"
)
async def create_ritual(
    request: RitualRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RitualResponse:
    
    try:
        # 인증된 사용자 ID 사용
        user_id = current_user.id
        
        # 기존 리츄얼 개수 확인
        stmt = select(func.count()).select_from(Ritual).where(Ritual.user_id == user_id)
        result = await db.execute(stmt)
        ritual_count = result.scalar() or 0
        
        # 새 리츄얼 시퀀스
        new_sequence = ritual_count + 1
        
        # 리츄얼 저장
        today = datetime.utcnow().date()
        ritual = Ritual(
            user_id=user_id,
            ritual_sequence=new_sequence,
            diary_entry=request.diary_entry,
            selected_mood=request.selected_mood,
            ritual_completed=True,
            checkin_date=today
        )
        db.add(ritual)
        await db.flush()
        
        # DailyRitual에도 저장 (대시보드 연동)
        from app.models.daily import DailyRitual, UserStreak
        
        # 오늘의 DailyRitual 확인 또는 생성
        stmt = select(DailyRitual).where(
            DailyRitual.user_id == user_id,
            DailyRitual.date == today
        )
        result = await db.execute(stmt)
        daily_ritual = result.scalar_one_or_none()
        
        if not daily_ritual:
            daily_ritual = DailyRitual(
                user_id=user_id,
                date=today,
                ritual_title="오늘의 리츄얼",
                ritual_description=f"기분: {request.selected_mood}",
                ritual_type="diary",
                duration_minutes=10,
                is_completed=True,
                completed_at=datetime.utcnow(),
                user_note=request.diary_entry,
                user_mood=request.selected_mood
            )
            db.add(daily_ritual)
        else:
            daily_ritual.is_completed = True
            daily_ritual.completed_at = datetime.utcnow()
            daily_ritual.user_note = request.diary_entry
            daily_ritual.user_mood = request.selected_mood
        
        # UserStreak 업데이트
        stmt = select(UserStreak).where(UserStreak.user_id == user_id)
        result = await db.execute(stmt)
        streak = result.scalar_one_or_none()
        
        if not streak:
            streak = UserStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
                total_days_active=1,
                total_rituals_completed=1
            )
            db.add(streak)
        else:
            # 어제 리츄얼 확인
            yesterday = today - timedelta(days=1)
            stmt = select(DailyRitual).where(
                DailyRitual.user_id == user_id,
                DailyRitual.date == yesterday,
                DailyRitual.is_completed == True
            )
            result = await db.execute(stmt)
            yesterday_ritual = result.scalar_one_or_none()
            
            if yesterday_ritual:
                # 연속 기록 유지
                streak.current_streak += 1
                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak
            else:
                # 연속 기록 초기화
                streak.current_streak = 1
            
            streak.total_days_active += 1
            streak.total_rituals_completed += 1
        
        await db.flush()
        
        # 마음나무 상태 업데이트 또는 생성
        stmt = select(HeartTree).where(HeartTree.user_id == user_id)
        result = await db.execute(stmt)
        heart_tree = result.scalar_one_or_none()
        
        if not heart_tree:
            heart_tree = HeartTree(
                user_id=user_id,
                growth_level=new_sequence,
                last_grew_at=datetime.utcnow()
            )
            db.add(heart_tree)
        else:
            heart_tree.growth_level = new_sequence
            heart_tree.last_grew_at = datetime.utcnow()
        
        # 마음나무 단계 계산
        tree_status = _calculate_tree_status(new_sequence)
        
        # 페르소나 업데이트 (5개 리츄얼마다)
        persona_updated = False
        persona_data = {}
        
        if new_sequence % 5 == 0:  # 5, 10, 15, 20, 25개째
            # 이전 리츄얼 데이터 가져오기
            stmt = select(Ritual).where(
                Ritual.user_id == user_id
            ).order_by(Ritual.ritual_sequence.desc()).limit(5)
            result = await db.execute(stmt)
            recent_rituals = result.scalars().all()
            
            # 워크플로우 실행
            workflow = MeariWorkflow()
            
            workflow_request = {
                "request_type": "ritual",
                "endpoint": "/api/rituals",
                "diary_entry": request.diary_entry,
                "selected_mood": request.selected_mood,
                "previous_rituals": [
                    {
                        "sequence": r.ritual_sequence,
                        "diary": r.diary_entry,
                        "mood": r.selected_mood
                    }
                    for r in recent_rituals
                ],
                "user_id": str(user_id)
            }
            
            workflow_result = workflow.process_request(workflow_request)
            workflow.close()
            
            # 페르소나 업데이트
            persona_data = workflow_result.get("persona", {})
            if persona_data:
                # 기존 페르소나를 is_latest=False로
                from sqlalchemy import update
                stmt = update(AIPersonaHistory).where(
                    AIPersonaHistory.user_id == user_id,
                    AIPersonaHistory.is_latest == True
                ).values(is_latest=False)
                await db.execute(stmt)
                
                # 새 페르소나 저장
                persona_history = AIPersonaHistory(
                    user_id=user_id,
                    persona_data=persona_data,
                    event_type="ritual_update",
                    is_latest=True,
                    event_date=datetime.utcnow().date()
                )
                db.add(persona_history)
                persona_updated = True
        
        # 28일 완주 처리
        completion_message = None
        if new_sequence == 28:
            completion_message = "축하합니다! 28일의 여정을 완주하셨습니다! 당신의 성장 일기가 생성되었습니다."
        
        await db.commit()
        
        return RitualResponse(
            status="success",
            action="ritual_recorded",
            timestamp=datetime.utcnow(),
            ritual_id=ritual.id,
            persona={
                "updated": persona_updated,
                "depth": persona_data.get("depth", "surface"),
                "summary": persona_data.get("summary", "")
            },
            tree=tree_status,
            message=completion_message or _get_encouragement_message(new_sequence)
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리츄얼 기록 중 오류 발생: {str(e)}"
        )


def _calculate_tree_status(ritual_count: int) -> TreeStatus:
    """마음나무 상태 계산"""
    
    if ritual_count <= 6:
        stage = "seed"
        stage_label = "씨앗"
        next_milestone = 7
    elif ritual_count <= 13:
        stage = "sprouting"
        stage_label = "새싹"
        next_milestone = 14
    elif ritual_count <= 20:
        stage = "growing"
        stage_label = "성장"
        next_milestone = 21
    elif ritual_count <= 27:
        stage = "blooming"
        stage_label = "개화"
        next_milestone = 28
    else:
        stage = "full_bloom"
        stage_label = "만개"
        next_milestone = None
    
    percentage = min(ritual_count / 28 * 100, 100)
    
    return TreeStatus(
        stage=stage,
        stage_label=stage_label,
        progress=ritual_count,
        next_milestone=next_milestone,
        percentage=percentage
    )


def _get_encouragement_message(ritual_count: int) -> str:
    """격려 메시지 생성"""
    
    milestones = {
        1: "첫 걸음을 내디뎠네요! 앞으로의 여정이 기대됩니다.",
        7: "일주일째 함께하고 있어요. 마음나무가 새싹을 틔웠어요!",
        14: "2주간의 여정, 대단해요! 마음나무가 무럭무럭 자라고 있어요.",
        21: "3주차, 거의 다 왔어요! 마음나무에 꽃봉오리가 맺혔어요.",
        28: "완주 축하합니다! 마음나무가 아름답게 만개했어요!"
    }
    
    if ritual_count in milestones:
        return milestones[ritual_count]
    else:
        return f"{ritual_count}일째 성장 중! 오늘도 한 걸음 더 나아갔어요."