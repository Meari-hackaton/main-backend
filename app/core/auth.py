"""
인증 관련 유틸리티 및 미들웨어
"""
from typing import Optional
from datetime import datetime
from fastapi import Depends, HTTPException, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User, UserSession


async def get_current_user(
    session_id: Optional[str] = Cookie(None, alias="meari_session"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    세션 쿠키를 통해 현재 로그인한 사용자를 가져옵니다.
    
    Args:
        session_id: 세션 쿠키 값
        db: 데이터베이스 세션
        
    Returns:
        User: 인증된 사용자 객체
        
    Raises:
        HTTPException: 인증 실패 시
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다",
            headers={"WWW-Authenticate": "Cookie"},
        )
    
    # 세션 조회
    stmt = select(UserSession).where(
        UserSession.session_id == session_id,
        UserSession.expires_at > datetime.utcnow()
    )
    result = await db.execute(stmt)
    user_session = result.scalar_one_or_none()
    
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="세션이 만료되었거나 유효하지 않습니다",
            headers={"WWW-Authenticate": "Cookie"},
        )
    
    # 사용자 조회
    stmt = select(User).where(User.id == user_session.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )
    
    return user


async def get_optional_user(
    session_id: Optional[str] = Cookie(None, alias="meari_session"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    선택적 인증 - 로그인하지 않아도 접근 가능하지만 로그인 시 사용자 정보 제공
    
    Args:
        session_id: 세션 쿠키 값
        db: 데이터베이스 세션
        
    Returns:
        Optional[User]: 인증된 사용자 객체 또는 None
    """
    if not session_id:
        return None
    
    try:
        # 세션 조회
        stmt = select(UserSession).where(
            UserSession.session_id == session_id,
            UserSession.expires_at > datetime.utcnow()
        )
        result = await db.execute(stmt)
        user_session = result.scalar_one_or_none()
        
        if not user_session:
            return None
        
        # 사용자 조회
        stmt = select(User).where(User.id == user_session.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        return user
    except Exception:
        return None