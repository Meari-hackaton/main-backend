"""
간단한 자체 인증 시스템 (username 버전)
"""
from fastapi import APIRouter, HTTPException, Depends, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
import uuid
import os

from app.core.database import get_db
from app.models.user import User, UserSession

router = APIRouter(prefix="/auth", tags=["auth"])

# 비밀번호 암호화
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "meari_session")
SESSION_EXPIRES_DAYS = int(os.getenv("SESSION_EXPIRES_DAYS", "7"))

# 요청/응답 스키마
class SignUpRequest(BaseModel):
    username: str  # 아이디 (이메일 아님)
    password: str
    nickname: str = None  # 닉네임은 선택사항

class LoginRequest(BaseModel):
    username: str  # 아이디로 로그인
    password: str

class AuthResponse(BaseModel):
    id: str
    username: str
    nickname: str = None
    message: str

# 비밀번호 해싱
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignUpRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """회원가입 - username/password 방식"""
    
    # username을 email 필드에 저장 (DB 구조 재활용)
    result = await db.execute(
        select(User).where(User.email == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용중인 아이디입니다"
        )
    
    # 사용자 생성 (email 필드에 username 저장)
    user = User(
        id=uuid.uuid4(),
        email=request.username,  # username을 email 필드에 저장
        password=hash_password(request.password),
        nickname=request.nickname or request.username,  # 닉네임 없으면 아이디 사용
        is_active=True
    )
    db.add(user)
    
    # 세션 생성
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRES_DAYS)
    
    user_session = UserSession(
        session_id=session_id,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(user_session)
    
    await db.commit()
    await db.refresh(user)
    
    # 쿠키 설정
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,  # HTTP 환경
        samesite="lax",
        max_age=SESSION_EXPIRES_DAYS * 24 * 60 * 60,
        path="/"
    )
    
    return AuthResponse(
        id=str(user.id),
        username=user.email,  # email 필드에서 username 반환
        nickname=user.nickname,
        message="회원가입이 완료되었습니다"
    )

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """로그인 - username/password"""
    
    # username으로 사용자 조회 (email 필드 사용)
    result = await db.execute(
        select(User).where(User.email == request.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다"
        )
    
    # 비밀번호 검증
    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다"
        )
    
    # 기존 세션 삭제
    await db.execute(
        select(UserSession).where(UserSession.user_id == user.id)
    )
    
    # 새 세션 생성
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRES_DAYS)
    
    user_session = UserSession(
        session_id=session_id,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(user_session)
    await db.commit()
    
    # 쿠키 설정
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_EXPIRES_DAYS * 24 * 60 * 60,
        path="/"
    )
    
    return AuthResponse(
        id=str(user.id),
        username=user.email,  # email 필드에서 username 반환
        nickname=user.nickname,
        message="로그인 성공"
    )