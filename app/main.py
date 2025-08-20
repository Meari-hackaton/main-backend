from fastapi import FastAPI, Depends, HTTPException, Query, Response
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

    # 6) 리다이렉트 또는 성공 응답
    return JSONResponse({
        "message": "Login successful",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "nickname": user.nickname
        }
    })

@app.get("/")
async def root():
    return {"message": "Meari Backend API", "version": "1.0.0"}