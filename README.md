# Meari Backend

메아리(Meari) - 사회적 고립을 겪는 청년을 위한 AI 심리회복 서비스 백엔드

## 프로젝트 구조

```
meari-backend/
├── app/                # 메인 애플리케이션
│   ├── api/           # API 엔드포인트
│   ├── core/          # 핵심 설정
│   ├── models/        # SQLAlchemy 모델
│   ├── schemas/       # Pydantic 스키마
│   └── services/      # 비즈니스 로직
├── scripts/           # 유틸리티 스크립트
└── tests/            # 테스트 코드
```

## 시작하기

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 수정
```

### 2. 데이터베이스 설정

```bash
# PostgreSQL 데이터베이스 생성
createdb meari_db

# 마이그레이션 실행
alembic upgrade head
```

### 3. 서버 실행

```bash
uvicorn app.main:app --reload
```

## API 문서

서버 실행 후 http://localhost:8000/docs 에서 Swagger UI 확인 가능