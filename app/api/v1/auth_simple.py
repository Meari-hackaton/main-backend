"""
간단한 자체 인증 시스템 (EC2 배포용)
"""
from fastapi import APIRouter, HTTPException, Depends, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
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
    email: str = Field(..., description="아이디", min_length=3, max_length=50)  # 아이디로 사용
    password: str = Field(..., description="비밀번호", min_length=4)
    nickname: str = Field(..., description="닉네임", min_length=2, max_length=20)

class LoginRequest(BaseModel):
    email: str = Field(..., description="아이디")  # 아이디로 사용
    password: str = Field(..., description="비밀번호")

class AuthResponse(BaseModel):
    id: str
    email: str
    nickname: str
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
    """회원가입 - 간단한 이메일/비밀번호 방식"""
    
    # 이메일 중복 체크
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용중인 아이디입니다"
        )
    
    # 사용자 생성
    user = User(
        id=uuid.uuid4(),
        email=request.email,
        password=hash_password(request.password),
        nickname=request.nickname,
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
    
    # 쿠키 설정 (HTTP 환경)
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
        email=user.email,
        nickname=user.nickname,
        message="회원가입이 완료되었습니다"
    )

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """로그인"""
    
    # 사용자 조회
    result = await db.execute(
        select(User).where(User.email == request.email)
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
        secure=False,  # HTTP 환경
        samesite="lax",
        max_age=SESSION_EXPIRES_DAYS * 24 * 60 * 60,
        path="/"
    )
    
    return AuthResponse(
        id=str(user.id),
        email=user.email,
        nickname=user.nickname,
        message="로그인 성공"
    )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """로그아웃"""
    
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    
    if session_id:
        # 세션 삭제
        result = await db.execute(
            select(UserSession).where(UserSession.session_id == session_id)
        )
        user_session = result.scalar_one_or_none()
        
        if user_session:
            await db.delete(user_session)
            await db.commit()
    
    # 쿠키 삭제
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=None
    )
    
    return {"message": "로그아웃 성공"}

@router.get("/check")
async def check_auth(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """인증 상태 확인"""
    
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    
    if not session_id:
        return {"authenticated": False}
    
    # 세션 확인
    result = await db.execute(
        select(UserSession).where(
            UserSession.session_id == session_id,
            UserSession.expires_at > datetime.utcnow()
        )
    )
    user_session = result.scalar_one_or_none()
    
    if not user_session:
        return {"authenticated": False}
    
    # 사용자 정보 조회
    result = await db.execute(
        select(User).where(User.id == user_session.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "nickname": user.nickname
        }
    }