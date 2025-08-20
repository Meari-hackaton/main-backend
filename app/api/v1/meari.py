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
    MeariSessionResponse,
    GrowthContentRequest,
    GrowthContentResponse
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
            "request_type": "initial_session",
            "endpoint": "/api/meari-sessions",
            "tag_ids": [request.selected_tag_id],  # 배열로 전달
            "user_context": request.user_context or f"태그 {request.selected_tag_id}번 관련 고민"
        }
        
        workflow_result = workflow.process_request(workflow_request)
        workflow.close()
        
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
        
        # user_id 처리
        if request.user_id:
            user_id = request.user_id
        else:
            # 테스트용 기본 사용자 생성 또는 조회
            from app.models.user import User
            from sqlalchemy import select
            
            # 테스트 사용자 조회
            result = await db.execute(
                select(User).where(User.email == "test@meari.com")
            )
            test_user = result.scalar_one_or_none()
            
            if not test_user:
                # 테스트 사용자 생성 (소셜 로그인 기반 User 모델)
                test_user = User(
                    id=uuid.uuid4(),
                    social_provider="test",
                    social_id="test_user_001",
                    email="test@meari.com",
                    nickname="테스트 사용자"
                )
                db.add(test_user)
                await db.flush()  # ID 즉시 사용 가능하도록
            
            user_id = test_user.id
        
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
    db: Session = Depends(get_db)
) -> GrowthContentResponse:
    
    try:
        # 세션 확인
        from sqlalchemy import select
        stmt = select(MeariSession).where(MeariSession.session_id == request.session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )
        
        # 사용자 ID 확인 또는 생성
        user_id = request.user_id or session.user_id
        if not user_id:
            # 테스트용 사용자 생성
            from app.models.user import User
            test_user = User(
                email=f"test_{uuid.uuid4().hex[:8]}@meari.com",
                full_name="테스트 사용자",
                is_active=True
            )
            db.add(test_user)
            await db.flush()
            user_id = test_user.id
        
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
        
        # 워크플로우 실행
        workflow = MeariWorkflow()
        
        workflow_request = {
            "request_type": "growth_content",
            "endpoint": "/api/growth-contents",
            "context": request.context,
            "session_id": str(request.session_id),
            "persona_summary": persona_summary,
            "previous_policy_ids": request.previous_policy_ids,
            "user_id": str(user_id) if user_id else None
        }
        
        workflow_result = workflow.process_request(workflow_request)
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