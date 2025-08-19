import os
import datetime
from typing import Optional

from fastapi import FastAPI, Request, Response, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, auth

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, text
from sqlalchemy.future import select

import httpx
from urllib.parse import urlencode


# --------------------------------------------------------------
# 환경 변수 로드
# --------------------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session")
SESSION_EXPIRES_DAYS = int(os.getenv("SESSION_EXPIRES_DAYS", "5"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL(.env)가 필요합니다!")
if not FIREBASE_CREDENTIALS:
    raise RuntimeError("FIREBASE_CREDENTIALS(.env)가 필요합니다!")

# --------------------------------------------------------------
# Firebase 초기화
# --------------------------------------------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)

# --------------------------------------------------------------
# DB 초기화
# --------------------------------------------------------------
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    provider_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_provider_provider_id"),
    )


# 테이블 생성
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --------------------------------------------------------------
# FastAPI 앱 생성 및 미들웨어 설정
# --------------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------
# DB 세션 의존성
# --------------------------------------------------------------
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


# --------------------------------------------------------------
# DB 조작
# --------------------------------------------------------------
async def find_user(db: AsyncSession, provider: str, provider_id: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.provider == provider, User.provider_id == provider_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, provider: str, provider_id: str, email: Optional[str], name: Optional[str]) -> User:
    user = User(provider=provider, provider_id=provider_id, email=email, name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# --------------------------------------------------------------
# Firebase 세션 로그인 & 로그아웃 엔드포인트
# --------------------------------------------------------------
@app.post("/auth/sessionLogin")
async def session_login(request: Request, response: Response):
    body = await request.json()
    id_token: Optional[str] = body.get("idToken")
    if not id_token:
        return JSONResponse({"error": "idToken required"}, status_code=400)

    try:
        expires_in = datetime.timedelta(days=SESSION_EXPIRES_DAYS)
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
    except Exception:
        return JSONResponse({"error": "Failed to create session cookie"}, status_code=401)

    cookie_params = {
        "key": SESSION_COOKIE_NAME,
        "value": session_cookie,
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "max_age": int(expires_in.total_seconds()),
        "path": "/",
    }
    if COOKIE_DOMAIN:
        cookie_params["domain"] = COOKIE_DOMAIN

    response.set_cookie(**cookie_params)
    return {"message": "session created"}


@app.post("/auth/sessionLogout")
async def session_logout(request: Request, response: Response):
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if session_cookie:
        try:
            decoded = auth.verify_session_cookie(session_cookie, check_revoked=False)
            uid = decoded.get("uid")
            if uid:
                auth.revoke_refresh_tokens(uid)
        except Exception:
            pass

    response.delete_cookie(SESSION_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN if COOKIE_DOMAIN else None)
    return {"message": "logged out"}

# --------------------------------------------------------------
# 인증 사용자 확인 유틸
# --------------------------------------------------------------
async def verify_firebase_session(request: Request) -> dict:
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        decoded = auth.verify_session_cookie(session_cookie, check_revoked=True)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    decoded = await verify_firebase_session(request)
    uid = decoded.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid session")

    email = decoded.get("email")
    name = decoded.get("name")

    user = await find_user(db, provider="firebase", provider_id=uid)
    if not user:
        user = await create_user(db, provider="firebase", provider_id=uid, email=email, name=name)
    return user


# --------------------------------------------------------------
# Google OAuth 로그인
# --------------------------------------------------------------
@app.get("/auth/google/login")
def google_login():
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
    async with httpx.AsyncClient() as client:
        # 1) 구글 인증 토큰 요청
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": "http://localhost:8000/auth/google/callback",
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")  # 추가로 id_token도 받아야 Firebase 세션 생성 가능

        if not access_token or not id_token:
            return JSONResponse({"error": "Failed to get access or ID token"}, status_code=400)

        # 2) 사용자 정보 요청
        userinfo_resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo_resp.raise_for_status()
        user_info = userinfo_resp.json()
        google_uid = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")

        if not google_uid:
            raise HTTPException(status_code=400, detail="Invalid user info from Google")

    # 3) DB 사용자 조회 및 생성
    user = await find_user(db, provider="google", provider_id=google_uid)
    if not user:
        user = await create_user(db, provider="google", provider_id=google_uid, email=email, name=name)

    # 4) Firebase 사용자 조회 또는 생성
    try:
        firebase_user = firebase_auth.get_user_by_email(email)
    except firebase_auth.UserNotFoundError:
        firebase_user = firebase_auth.create_user(email=email, display_name=name)

    # 5) Firebase 세션 쿠키 생성
    expires_in = datetime.timedelta(days=SESSION_EXPIRES_DAYS)
    try:
        session_cookie = firebase_auth.create_session_cookie(id_token, expires_in=expires_in)
    except Exception:
        return JSONResponse({"error": "Failed to create Firebase session cookie"}, status_code=401)

    # 6) 쿠키 세팅 (클라이언트에 세션쿠키 발급)
    cookie_params = {
        "key": SESSION_COOKIE_NAME,
        "value": session_cookie,
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "max_age": int(expires_in.total_seconds()),
        "path": "/",
    }
    if COOKIE_DOMAIN:
        cookie_params["domain"] = COOKIE_DOMAIN

    response.set_cookie(**cookie_params)

    # 7) 로그인 완료 응답 (필요에 따라 추가 정보 반환)
    return {"message": "Google OAuth 및 Firebase 세션 로그인 완료", "user": {"id": user.id, "email": user.email, "name": user.name}}



@app.get("/")
async def root():
    return RedirectResponse(url="/docs")
