import os
import datetime
from typing import Optional

from fastapi import FastAPI, Request, Response, Depends, HTTPException, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth

# SQLAlchemy (PostgreSQL via DATABASE_URL)
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, UniqueConstraint, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# -----------------------------------------------------------------------------
# .env 세팅
# -----------------------------------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")  # 서비스 계정 JSON 파일 경로

# 쿠키/세션 설정
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session")
SESSION_EXPIRES_DAYS = int(os.getenv("SESSION_EXPIRES_DAYS", "5"))  # Firebase 세션 쿠키 만료일수
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"  # HTTPS 환경에서 true 권장
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()  # 'lax' | 'strict' | 'none'
COOKIE_DOMAIN: Optional[str] = os.getenv("COOKIE_DOMAIN")  # 필요 시 도메인 지정

# -----------------------------------------------------------------------------
# Firebase 초기화
# -----------------------------------------------------------------------------
if not firebase_admin._apps:  # 중복 초기화 방지
    if not FIREBASE_CREDENTIALS:
        raise RuntimeError("FIREBASE_CREDENTIALS(.env)가 필요합니다: 서비스 계정 JSON 경로")
    cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)

# -----------------------------------------------------------------------------
# DB 초기화 (SQLAlchemy)
# -----------------------------------------------------------------------------
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL(.env)가 필요합니다: e.g. postgresql+psycopg2://...")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    provider_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    picture = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_provider_provider_id"),
    )

# 테이블 생성
Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# FastAPI 앱
# -----------------------------------------------------------------------------
app = FastAPI()

# CORS (프론트 도메인에 맞춰 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# DB 유틸
# -----------------------------------------------------------------------------

def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    finally:
        ...


def find_user(db: Session, provider: str, provider_id: str) -> Optional[User]:
    return db.query(User).filter(User.provider == provider, User.provider_id == provider_id).first()


def create_user(db: Session, provider: str, provider_id: str, email: Optional[str], name: Optional[str], picture: Optional[str]) -> User:
    user = User(provider=provider, provider_id=provider_id, email=email, name=name, picture=picture)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def find_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# -----------------------------------------------------------------------------
# Firebase 기반 세션 로그인 플로우
#  - 프론트엔드에서 Firebase로 로그인 → idToken을 /auth/sessionLogin에 전달
#  - 서버는 idToken으로 Firebase 세션쿠키 생성해 HttpOnly 쿠키로 저장
#  - 이후 요청은 쿠키를 기반으로 인증 (stateless JWT 대신 stateful-like session cookie)
# -----------------------------------------------------------------------------

@app.post("/auth/sessionLogin")
async def session_login(request: Request, response: Response):
    body = await request.json()
    id_token: Optional[str] = body.get("idToken")
    if not id_token:
        return JSONResponse({"error": "idToken required"}, status_code=400)

    # 세션 쿠키 생성 (Firebase 관리)
    try:
        expires_in = datetime.timedelta(days=SESSION_EXPIRES_DAYS)
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
    except Exception as e:
        return JSONResponse({"error": "Failed to create session cookie"}, status_code=401)

    # 쿠키 설정
    cookie_params = {
        "key": SESSION_COOKIE_NAME,
        "value": session_cookie,
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,  # cross-site라면 'none' + secure 필요
        "max_age": int(expires_in.total_seconds()),
        "path": "/",
    }
    if COOKIE_DOMAIN:
        cookie_params["domain"] = COOKIE_DOMAIN

    response.set_cookie(**cookie_params)
    return {"message": "session created"}


@app.post("/auth/sessionLogout")
async def session_logout(request: Request, response: Response):
    # 현재 세션 쿠키 검증 → 해당 uid의 refresh tokens revoke
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if session_cookie:
        try:
            decoded = auth.verify_session_cookie(session_cookie, check_revoked=False)
            uid = decoded.get("uid")
            if uid:
                # 모든 기존 세션 무효화
                auth.revoke_refresh_tokens(uid)
        except Exception:
            pass

    response.delete_cookie(SESSION_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN if COOKIE_DOMAIN else None)
    return {"message": "logged out"}

# -----------------------------------------------------------------------------
# 인증된 사용자 유틸
# -----------------------------------------------------------------------------

def verify_firebase_session(request: Request) -> dict:
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        # check_revoked=True로 설정하면 revoke_refresh_tokens 이후의 쿠키는 거부됨
        decoded = auth.verify_session_cookie(session_cookie, check_revoked=True)
        return decoded  # { 'uid': '...', 'email': '...', 'name': '...', 'picture': '...' }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def get_current_user(request: Request):
    decoded = verify_firebase_session(request)
    uid = decoded.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid session")

    email = decoded.get("email")
    name = decoded.get("name")
    picture = decoded.get("picture")

    db = SessionLocal()
    try:
        user = find_user(db, provider="firebase", provider_id=uid)
        if not user:
            user = create_user(db, provider="firebase", provider_id=uid, email=email, name=name, picture=picture)
        return user
    finally:
        db.close()

# -----------------------------------------------------------------------------
# API 엔드포인트
# -----------------------------------------------------------------------------

@app.get("/profile")
def profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "provider": user.provider,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
    }


@app.get("/")
async def root():
    # 필요 시 프론트 페이지로 리디렉션
    return RedirectResponse(url="/docs")
