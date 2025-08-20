from fastapi import FastAPI, Depends, HTTPException, Query, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from urllib.parse import urlencode
import httpx
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, get_optional_user
from app.api.v1.api import api_router
from app.models.user import User, UserSession

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url="/api/v1/openapi.json",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # React 개발 서버 및 개발용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# OAuth 환경 변수
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "meari_session")
SESSION_EXPIRES_DAYS = int(os.getenv("SESSION_EXPIRES_DAYS", "7"))

# --------------------------------------------------------------
# DB 조작 헬퍼 함수
# --------------------------------------------------------------
async def find_user(db: AsyncSession, provider: str, provider_id: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.social_provider == provider, User.social_id == provider_id)
    )
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, provider: str, provider_id: str, email: str, nickname: Optional[str]) -> User:
    user = User(
        id=uuid.uuid4(),
        social_provider=provider,
        social_id=provider_id,
        email=email,
        nickname=nickname
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# --------------------------------------------------------------
# Google OAuth 로그인
# --------------------------------------------------------------
@app.get("/auth/google/login")
def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": "http://localhost:8001/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline"
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)

# --------------------------------------------------------------
# Google OAuth 콜백 처리
# --------------------------------------------------------------
@app.get("/auth/google/callback")
async def google_callback(
    response: Response,
    db: AsyncSession = Depends(get_db),
    code: str = Query(...)
):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        # 1) 구글 인증 토큰 요청
        token_resp = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": "http://localhost:8001/auth/google/callback",
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # 2) 사용자 정보 요청
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_info = userinfo_resp.json()
        google_uid = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")

        if not google_uid or not email:
            raise HTTPException(status_code=400, detail="Invalid user info from Google")

    # 3) DB 사용자 조회 및 생성
    user = await find_user(db, provider="google", provider_id=google_uid)
    if not user:
        user = await create_user(db, provider="google", provider_id=google_uid, email=email, nickname=name)

    # 4) 세션 생성
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRES_DAYS)
    
    user_session = UserSession(
        session_id=session_id,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(user_session)
    await db.commit()

    # 5) 쿠키 설정
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,  # 개발 환경에서는 False
        samesite="lax",
        max_age=SESSION_EXPIRES_DAYS * 24 * 60 * 60,
        path="/"
    )

    # 6) 프론트엔드로 리다이렉트
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/dashboard?login=success")

# --------------------------------------------------------------
# 사용자 정보 API
# --------------------------------------------------------------
@app.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 반환"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "nickname": current_user.nickname,
        "social_provider": current_user.social_provider,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

# --------------------------------------------------------------
# 로그아웃 API
# --------------------------------------------------------------
@app.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """로그아웃 - 세션 삭제 및 쿠키 제거"""
    
    # 세션 찾기
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        # 세션 삭제
        result = await db.execute(
            select(UserSession).where(
                UserSession.session_id == session_id,
                UserSession.user_id == current_user.id
            )
        )
        user_session = result.scalar_one_or_none()
        
        if user_session:
            await db.delete(user_session)
            await db.commit()
    
    # 쿠키 제거
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=None
    )
    
    return {"message": "로그아웃 성공"}

@app.get("/")
async def root():
    return {"message": "Meari Backend API", "version": "1.0.0"}