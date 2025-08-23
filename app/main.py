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
# from app.core.workflow_manager import initialize_workflow
from app.api.v1.api import api_router
from app.api.v1.auth_simple import router as auth_router  # 자체 인증 추가
from app.models.user import User, UserSession

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url="/api/v1/openapi.json",
)

# CORS 설정 (EC2 배포 포함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://localhost:8001",
        "http://ec2-13-209-5-24.ap-northeast-2.compute.amazonaws.com",  # 새 Frontend EC2
        "http://13.209.5.24",  # 새 Frontend IP 직접 접근
        "http://ec2-43-200-4-71.ap-northeast-2.compute.amazonaws.com",  # 이전 Frontend (임시 유지)
        "http://ec2-43-200-4-71.ap-northeast-2.compute.amazonaws.com:3000",
        "http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com",  # Backend EC2
        "http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000",
        # "*" 제거 - withCredentials와 충돌
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(auth_router, prefix="/api/v1")  # 자체 인증 API
app.include_router(api_router, prefix="/api/v1")   # 기존 API

# @app.on_event("startup")
# async def startup_event():
#     """서버 시작 시 워크플로우 및 연결 초기화"""
#     # initialize_workflow()
#     print(f"🌐 API 문서: http://localhost:8001/docs")

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
        "redirect_uri": "http://localhost:8000/auth/google/callback",
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
                "redirect_uri": "http://localhost:8000/auth/google/callback",
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

    # 5) 프론트엔드로 리다이렉트 (쿠키 포함)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    # 신규 회원이면 steps로, 기존 회원이면 dashboard로
    from datetime import timezone
    now = datetime.now(timezone.utc) if user.created_at and user.created_at.tzinfo else datetime.utcnow()
    
    if user.created_at:
        # created_at이 timezone-aware인 경우 처리
        created_at = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=timezone.utc)
        if (now - created_at).total_seconds() < 60:
            # 방금 생성된 사용자 (1분 이내)
            response = RedirectResponse(f"{frontend_url}/steps?login=success")
        else:
            # 기존 사용자
            response = RedirectResponse(f"{frontend_url}/dashboard?login=success")
    else:
        # created_at이 없는 경우 dashboard로
        response = RedirectResponse(f"{frontend_url}/dashboard?login=success")
    
    # 6) 리다이렉트 응답에 쿠키 설정
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,  # 개발 환경에서는 False
        samesite="lax",
        max_age=SESSION_EXPIRES_DAYS * 24 * 60 * 60,
        path="/"
    )
    
    return response

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

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (EC2 배포 확인용)"""
    return {
        "status": "healthy",
        "service": "meari-backend",
        "timestamp": datetime.utcnow().isoformat()
    }