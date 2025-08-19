"""
메아리 API 엔드포인트
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.core.database import get_db
from app.schemas.meari import (
    MeariSessionRequest,
    MeariSessionResponse
)
from app.models.card import MeariSession, GeneratedCard
from app.models.checkin import AIPersonaHistory
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
    db: Session = Depends(get_db)
) -> MeariSessionResponse:
    
    try:
        workflow = MeariWorkflow()
        
        workflow_request = {
            "type": "initial_session",
            "endpoint": "/api/meari-sessions",
            "tag_ids": [request.selected_tag_id],
            "user_context": request.user_context or f"태그 {request.selected_tag_id}번 관련 고민"
        }
        
        result = workflow.process_request(workflow_request)
        workflow.close()
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "워크플로우 처리 실패")
            )
        
        session_id = uuid.uuid4()
        
        session = MeariSession(
            id=session_id,
            user_id=request.user_id,
            selected_tag_ids=[request.selected_tag_id],
            created_at=datetime.utcnow()
        )
        db.add(session)
        
        cards_for_db = result.get("cards_for_db", [])
        for card_data in cards_for_db:
            card = GeneratedCard(
                session_id=session_id,
                user_id=request.user_id,
                card_type=card_data.get("card_type"),
                sub_type=card_data.get("sub_type"),
                content=card_data.get("content"),
                source_ids=card_data.get("source_ids"),
                growth_context=card_data.get("growth_context", "initial")
            )
            db.add(card)
        
        persona_data = result.get("persona", {})
        if persona_data and request.user_id:
            db.query(AIPersonaHistory).filter(
                AIPersonaHistory.user_id == request.user_id,
                AIPersonaHistory.is_latest == True
            ).update({"is_latest": False})
            
            persona_history = AIPersonaHistory(
                user_id=request.user_id,
                persona_data=persona_data,
                event_type="initial",
                is_latest=True,
                event_date=datetime.utcnow().date()
            )
            db.add(persona_history)
        
        db.commit()
        
        return MeariSessionResponse(
            status="success",
            session_type="initial",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            cards=result.get("cards", {}),
            persona=persona_data,
            next_action="growth_content"
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성 중 오류 발생: {str(e)}"
        )