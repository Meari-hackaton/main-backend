# 메아리(Meari) 백엔드 API 서버

청년의 마음 건강을 위한 AI 심리회복 서비스 백엔드

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택](#기술-스택)
3. [시작하기](#시작하기)
4. [환경 설정](#환경-설정)
5. [데이터베이스 설정](#데이터베이스-설정)
6. [서버 실행](#서버-실행)
7. [API 문서](#api-문서)
8. [트러블슈팅](#트러블슈팅)

## 프로젝트 개요

메아리는 사회적 고립을 겪는 청년을 위한 AI 기반 심리회복 서비스입니다.
- 공감 카드와 성찰 카드를 통한 정서적 지원
- 맞춤형 성장 콘텐츠 추천 (정보/경험/지원)
- 28일 리츄얼을 통한 마음나무 성장
- 페르소나 기반 개인화 서비스

## 기술 스택

- **Framework**: FastAPI 0.116.1
- **Database**: PostgreSQL + SQLAlchemy 2.0
- **Vector DB**: Milvus (Zilliz Cloud)
- **Graph DB**: Neo4j
- **AI/LLM**: Google Gemini, LangChain, LangGraph
- **Embedding**: KURE-v1 (한국어 특화)
- **Python**: 3.11+

## 시작하기

### 필수 준비사항
- Python 3.11+ (3.10도 가능)
- PostgreSQL 15+
- Neo4j 5.0+ (로컬 또는 Docker)
- Git

### 1. 저장소 클론
```bash
git clone https://github.com/your-org/meari-backend.git
cd meari-backend
```

### 2. Python 가상환경 설정
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

## 환경 설정

### 환경 변수 파일 설정
프로젝트 관리자로부터 `.env` 파일을 받아서 프로젝트 루트 디렉토리에 저장합니다.

**중요**: `.env` 파일은 절대 Git에 커밋하지 마세요!

## 데이터베이스 설정

### 1. PostgreSQL 설치 및 설정

#### Docker 사용 (권장)
```bash
# docker-compose.yml 파일이 있는 경우
docker-compose up -d

# 또는 직접 실행
docker run -d \
  --name meari-postgres \
  -e POSTGRES_DB=meari_db \
  -e POSTGRES_USER=meari_user \
  -e POSTGRES_PASSWORD=meari_password \
  -p 5432:5432 \
  postgres:15
```

#### 로컬 설치
```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. 데이터베이스 생성
```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 및 사용자 생성
CREATE DATABASE meari_db;
CREATE USER meari_user WITH PASSWORD 'meari_password';
GRANT ALL PRIVILEGES ON DATABASE meari_db TO meari_user;
\q
```

### 3. 테이블 초기화
```bash
# 테이블 생성
python -m app.db.init_db

# 태그 데이터 시딩
python -m app.db.seed_tags
```

### 4. Neo4j 설치

#### Docker 사용
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

#### Neo4j Desktop 설치 (권장)
1. [Neo4j Desktop](https://neo4j.com/download/) 다운로드
2. 새 프로젝트 생성 > 데이터베이스 생성
3. 데이터베이스 시작 (기본 포트: 7687)

### 5. Milvus 설정 (Zilliz Cloud)
1. [Zilliz Cloud](https://cloud.zilliz.com) 회원가입
2. Free Tier 클러스터 생성
3. Connection 정보에서 URI와 Token 복사
4. `.env` 파일에 설정

## 서버 실행

### 개발 서버 실행
```bash
# 자동 리로드 모드로 실행 (포트 8001)
uvicorn app.main:app --reload --port 8001

# 또는 python 모듈로 실행
python -m uvicorn app.main:app --reload --port 8001
```

### 프로덕션 서버 실행
```bash
# 워커 프로세스 4개로 실행
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

서버가 정상적으로 실행되면:
- API 서버: http://localhost:8001
- API 문서 (Swagger): http://localhost:8001/docs
- 대체 문서 (ReDoc): http://localhost:8001/redoc

## API 문서

### 주요 엔드포인트

#### 인증
- `GET /auth/login/{provider}` - 소셜 로그인 (google/kakao)
- `GET /auth/callback/{provider}` - OAuth 콜백
- `GET /auth/me` - 현재 사용자 정보

#### 메아리 세션
- `POST /api/v1/meari/sessions` - 초기 세션 생성 (공감/성찰 카드)
- `POST /api/v1/meari/growth-contents` - 성장 콘텐츠 생성
- `POST /api/v1/meari/rituals` - 리츄얼 기록

#### 대시보드
- `GET /api/v1/dashboard/` - 대시보드 메인
- `GET /api/v1/dashboard/calendar` - 월별 캘린더
- `POST /api/v1/dashboard/rituals` - 일일 리츄얼 생성
- `PATCH /api/v1/dashboard/rituals/{id}/complete` - 리츄얼 완료

### API 테스트
Swagger UI (http://localhost:8001/docs)에서 직접 테스트 가능합니다.

## 초기 데이터 수집 (선택사항)

프로젝트에 필요한 데이터를 수집하려면:

```bash
# 빅카인즈 뉴스 데이터 수집 (약 900개)
python scripts/collect_news.py

# 청년 정책 데이터 수집 (약 3,000개)
python scripts/collect_policies.py

# 인용문 추출 (뉴스에서)
python scripts/collect_quotes.py

# 벡터 DB 구축
python scripts/create_vector_collections.py

# 지식 그래프 구축 (Neo4j)
python scripts/build_knowledge_graph.py
```

## 트러블슈팅

### 1. 데이터베이스 연결 오류
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**해결**: PostgreSQL 서비스가 실행 중인지 확인
```bash
# Docker
docker ps | grep postgres

# 로컬
sudo systemctl status postgresql
```

### 2. Milvus 연결 실패
```
pymilvus.exceptions.ConnectionNotFoundError
```
**해결**: Zilliz Cloud URI와 Token이 올바른지 확인

### 3. Neo4j 연결 실패
```
neo4j.exceptions.ServiceUnavailable
```
**해결**: Neo4j가 실행 중이고 포트 7687이 열려있는지 확인

### 4. API 키 오류
```
google.generativeai.types.generation_types.BlockedPromptException
```
**해결**: Gemini API 키가 유효한지 확인

### 5. 모듈 import 오류
```
ModuleNotFoundError: No module named 'app'
```
**해결**: 프로젝트 루트 디렉토리에서 실행하는지 확인
```bash
cd meari-backend
python -m uvicorn app.main:app --reload
```

## 개발 팀

- Backend Development: Meari Team
- AI/ML Engineering: Meari Team
- Data Engineering: Meari Team

## 라이센스

This project is proprietary and confidential.

## 지원

문제가 발생하면:
1. [이슈 트래커](https://github.com/your-org/meari-backend/issues) 확인
2. 새 이슈 생성
3. 팀 슬랙 채널에 문의

---

**Note**: 이 README는 개발 환경 설정을 위한 가이드입니다. 프로덕션 배포 시에는 추가적인 보안 설정이 필요합니다.
