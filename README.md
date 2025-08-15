# Meari Backend

메아리(Meari) - 사회적 고립을 겪는 청년을 위한 AI 심리회복 서비스 백엔드

## 목차
1. [필수 준비사항](#필수-준비사항)
2. [프로젝트 설치 및 실행](#프로젝트-설치-및-실행)
3. [데이터베이스 구조](#데이터베이스-구조)
4. [회원 시스템 설계](#회원-시스템-설계)
5. [API 개발 가이드](#api-개발-가이드)
6. [문제 해결](#문제-해결)

## 필수 준비사항

### 1. Python 3.10 이상
```bash
# 버전 확인
python --version
# 또는
python3 --version
```

### 2. Docker Desktop
- [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/)
- 설치 후 실행 

### 3. Git
```bash
# 설치 확인
git --version
```

## 프로젝트 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/Meari-hackaton/main-backend.git
cd main-backend
```

### 2. Python 가상환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# 활성화 확인 (터미널 앞에 (venv) 뜨면 된겁니다)
```

### 3. 패키지 설치
```bash
# pip 최신 버전으로 업그레이드 (필수에요)
pip install --upgrade pip

# 전체 패키지 설치
pip install -r requirements.txt
```

**설치 에러 발생 시:**
```bash
# 핵심 패키지만 먼저 설치
pip install greenlet
pip install psycopg2-binary
pip install sqlalchemy asyncpg
pip install fastapi uvicorn
pip install pydantic-settings python-dotenv

# 다시 전체 설치 시도
pip install -r requirements.txt
```

### 4. Docker로 PostgreSQL 실행
```bash
# Docker Desktop 켜놓고 실행하면 됩니다

# PostgreSQL 컨테이너 시작
docker-compose up -d

# 실행 확인 (아래와 같이 나와야 함)
docker ps
# CONTAINER ID   IMAGE         ... STATUS         PORTS                    NAMES
# xxxxxx         postgres:16   ... Up X minutes   0.0.0.0:5432->5432/tcp   main-backend-db-1
```

### 5. 데이터베이스 테이블 생성
```bash
# 5초 정도 대기 (DB가 완전히 시작되도록)
sleep 5

# 테이블 생성
python -m app.db.init_db

# 성공 메시지 확인:
# 테이블 생성 완료
# 
# 생성된 테이블 목록:
#   - ai_persona_histories
#   - daily_checkins
#   - generated_cards
#   - heart_trees
#   - meari_sessions
#   - tags
#   - user_sessions
#   - users
```

### 6. 서버 실행
```bash
uvicorn app.main:app --reload

# 실행 확인:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 7. 접속 확인
- API 문서: http://localhost:8000/docs -- swagger
- 헬스체크: http://localhost:8000/ -- 서버 멀쩡한지 확인

## 데이터베이스 구조

### 주요 테이블
```
users               # 사용자 정보
├── user_sessions   # 로그인 세션
├── meari_sessions  # 분석 요청 기록
├── generated_cards # AI가 생성한 카드
├── daily_checkins  # 매일 체크인
├── heart_trees     # 마음나무 (1:1)
└── persona_histories # AI 페르소나 이력

tags                # 태그 마스터 데이터
```

### 데이터베이스 접속 정보
```
Host: localhost
Port: 5432
Database: meari_db
Username: meari_user
Password: meari_password
```

## 회원 시스템 설계

### 인증 방식: 세션 기반
- JWT 대신 서버 세션 사용 (구현 용이)
- 소셜 로그인만 지원 (Google, Kakao)
- 일반 회원가입 없음

### 회원 관련 테이블 구조

#### 1. users 테이블
```sql
- id: UUID (기본키)
- social_provider: 'google' 또는 'kakao'
- social_id: 소셜 서비스에서 받은 고유 ID
- email: 이메일 (unique)
- nickname: 닉네임
- created_at: 가입일시
```

#### 2. user_sessions 테이블
```sql
- session_id: 세션 ID (기본키)
- user_id: 사용자 ID (외래키)
- expires_at: 만료 시간
- created_at: 생성 시간
```

### 로그인 플로우
```
1. 프론트엔드 → 소셜 로그인 요청
2. 소셜 서비스 → 인증 후 콜백
3. 백엔드 → 사용자 정보 확인/생성
4. 백엔드 → 세션 생성 및 쿠키 발급
5. 프론트엔드 → 세션 쿠키로 인증 유지
```

### 구현 예시 (추후 개발)
```python
# app/api/v1/auth.py
@router.get("/auth/google")
async def google_login():
    # Google OAuth URL로 리다이렉트
    pass

@router.get("/auth/google/callback")
async def google_callback(code: str):
    # 1. Google에서 사용자 정보 받기
    # 2. DB에서 사용자 조회/생성
    # 3. 세션 생성
    # 4. 쿠키 설정 후 프론트엔드로 리다이렉트
    pass
```

## API 개발 가이드

### 파일 구조
```
app/
├── api/v1/
│   ├── auth.py      # 인증 관련 (소셜 로그인)
│   ├── users.py     # 사용자 정보
│   ├── cards.py     # 메아리 카드 생성/조회
│   ├── tags.py      # 태그 목록
│   └── checkins.py  # 데일리 체크인
```

### 인증이 필요한 API (상태관리에 필수로 상호작용되는 부분 프론트에서 전역으로 관리할 api 구조가 이런 형태?일겁니다.)
```python
from fastapi import Depends
from app.api.deps import get_current_user

@router.get("/me")
async def get_my_info(current_user: User = Depends(get_current_user)):
    return current_user
```

### API 명세 (구현 예정)
- `POST /api/v1/auth/google` - 구글 로그인
- `POST /api/v1/auth/kakao` - 카카오 로그인
- `POST /api/v1/auth/logout` - 로그아웃
- `GET /api/v1/me` - 내 정보
- `GET /api/v1/tags` - 태그 목록
- `POST /api/v1/cards` - 카드 생성
- `GET /api/v1/cards` - 내 카드 목록
- `POST /api/v1/checkins` - 데일리 체크인