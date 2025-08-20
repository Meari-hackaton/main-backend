# 메아리(Meari) 백엔드 API 서버

청년의 마음 건강을 위한 AI 심리회복 서비스 백엔드

## 🚀 빠른 시작 (Docker Compose 사용 - 권장)

### 팀원을 위한 가장 간단한 실행 방법

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/meari-backend.git
cd meari-backend

# 2. .env 파일 받기 (팀 리더에게 요청)
# .env 파일을 프로젝트 루트에 저장

# 3. Docker Compose로 전체 환경 실행 (PostgreSQL 포함)
docker-compose -f docker-compose-simple.yml up

# 서버가 http://localhost:8000 에서 실행됩니다
# API 문서: http://localhost:8000/docs
```

**Docker 설치 필요**: [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/)

### psql 없이도 작동합니다!
- Docker Compose가 PostgreSQL을 자동으로 설정
- 887개 뉴스, 3,977개 정책 등 모든 데이터 자동 로드
- Neo4j, Milvus는 클라우드 서비스 사용 (.env 파일에 설정됨)

---

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택](#기술-스택)
3. [설치 방법 선택](#설치-방법-선택)
4. [Docker 사용 (권장)](#docker-사용-권장)
5. [로컬 설치](#로컬-설치)
6. [API 문서](#api-문서)
7. [트러블슈팅](#트러블슈팅)

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
- **Graph DB**: Neo4j (Aura Cloud)
- **AI/LLM**: Google Gemini, LangChain, LangGraph
- **Embedding**: KURE-v1 (한국어 특화)
- **Python**: 3.12 (Docker) / 3.11+ (로컬)

## 설치 방법 선택

### 방법 1: Docker 사용 (권장) ✅
- PostgreSQL 설치 불필요
- 모든 데이터 자동 로드
- 팀원 간 환경 일치 보장

### 방법 2: 로컬 설치
- Python 가상환경 사용
- PostgreSQL 별도 설치 필요
- 개발 시 더 빠른 반응 속도

## Docker 사용 (권장)

### 필요한 파일
팀 리더로부터 받아야 할 파일:
1. **`.env`** - 환경 변수 파일 (API 키, 클라우드 DB 연결 정보)
2. **`meari_db_dump.sql`** - PostgreSQL 초기 데이터 (7.2MB)

### Docker Compose 파일 2종

#### 1. 개발/일반 사용 (docker-compose-simple.yml)
```bash
# 단일 앱 인스턴스 실행
docker-compose -f docker-compose-simple.yml up

# 백그라운드 실행
docker-compose -f docker-compose-simple.yml up -d

# 로그 확인
docker-compose -f docker-compose-simple.yml logs -f app

# 종료
docker-compose -f docker-compose-simple.yml down
```

#### 2. 30명 동시 테스트용 (docker-compose.yml)
```bash
# 6개 앱 인스턴스 + Nginx 로드밸런서
docker-compose up

# 30명 동시 테스트 실행
./test_concurrent_30.sh
```

### Docker 환경 초기화
```bash
# 모든 컨테이너와 볼륨 삭제 (데이터 초기화)
docker-compose down -v

# 다시 시작 (데이터 자동 재로드)
docker-compose -f docker-compose-simple.yml up
```

## 로컬 설치

### 필수 준비사항
- Python 3.11+ (3.13은 호환성 문제 있음)
- PostgreSQL 15+
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

### 4. PostgreSQL 설정

#### macOS (Homebrew)
```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### Windows
[PostgreSQL 공식 다운로드](https://www.postgresql.org/download/windows/)

### 5. 데이터베이스 생성 및 복원
```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE meari_db;
CREATE USER meari_user WITH PASSWORD 'meari_password';
GRANT ALL PRIVILEGES ON DATABASE meari_db TO meari_user;
\q

# 데이터 복원 (meari_db_dump.sql 파일 필요)
psql -U meari_user -d meari_db < meari_db_dump.sql
```

### 6. 서버 실행
```bash
# 개발 모드 (자동 리로드)
uvicorn app.main:app --reload --port 8001

# 또는
python -m uvicorn app.main:app --reload --port 8001
```

## 환경 변수 (.env)

필수 환경 변수 (팀 리더에게 요청):
```env
# Database
DATABASE_URL=postgresql+asyncpg://meari_user:meari_password@localhost/meari_db

# API Keys
GEMINI_API_KEY=your-gemini-api-key
BIGKINDS_ACCESS_KEY=your-bigkinds-key
YOUTH_POLICY_API_KEY=your-youth-policy-key

# Cloud Services (이미 데이터 준비됨)
MILVUS_URI=https://xxx.zillizcloud.com
MILVUS_TOKEN=your-milvus-token
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

# OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## 클라우드 서비스 상태

모든 클라우드 서비스는 이미 데이터가 준비되어 있습니다:
- **Milvus (Zilliz Cloud)**: ✅ 877개 인용문, 3,977개 정책 벡터
- **Neo4j (Aura Cloud)**: ✅ 5,262개 노드, 15,257개 관계
- **PostgreSQL**: Docker 사용 시 자동 로드, 로컬은 덤프 파일 복원 필요

⚠️ **중요**: Neo4j와 Milvus는 클라우드 서비스를 사용합니다. 
- 팀원들은 `.env` 파일의 연결 정보로 자동 연결됩니다
- 데이터 수집 스크립트(`scripts/collect_*.py`)는 실행하지 마세요 (이미 완료됨)
- 로컬 Neo4j/Milvus 설치 불필요

## API 문서

서버 실행 후:
- **Swagger UI**: http://localhost:8000/docs (Docker)
- **Swagger UI**: http://localhost:8001/docs (로컬)
- **ReDoc**: http://localhost:8000/redoc

### 주요 엔드포인트

#### 메아리 세션
- `POST /api/v1/meari/sessions` - 초기 세션 생성 (공감/성찰 카드)
- `POST /api/v1/meari/growth-contents` - 성장 콘텐츠 생성
- `POST /api/v1/meari/rituals` - 리츄얼 기록

#### 대시보드
- `GET /api/v1/dashboard/` - 대시보드 메인
- `GET /api/v1/dashboard/calendar` - 월별 캘린더
- `POST /api/v1/dashboard/rituals` - 일일 리츄얼 생성

## 트러블슈팅

### Docker 관련

#### 포트 충돌
```
Error: bind: address already in use
```
**해결**: 
```bash
# 기존 PostgreSQL 중지
sudo systemctl stop postgresql
# 또는 Docker Compose 포트 변경
```

#### 메모리 부족
```
Error: Cannot allocate memory
```
**해결**: Docker Desktop 설정에서 메모리 할당 증가 (최소 4GB)

### 로컬 설치 관련

#### psql 명령어 없음
```
command not found: psql
```
**해결**: Docker Compose 사용 또는 PostgreSQL 클라이언트 설치

#### Python 3.13 호환성 문제
```
RuntimeError: Could not parse python long as longdouble
```
**해결**: Python 3.12 또는 3.11 사용

### API 관련

#### 동시 사용자 제한
- 단일 인스턴스: 3-5명
- Docker Compose (6 인스턴스): 30명
- Gemini API 제한: 분당 10 요청

#### 응답 시간이 느림 (30-60초)
정상입니다. AI 처리에 시간이 필요합니다:
- 공감 카드: Vector RAG (Milvus)
- 성찰 카드: Graph RAG (Neo4j)
- 페르소나 생성: LLM 처리

## 개발 팁

### 로그 확인
```bash
# Docker 로그
docker-compose -f docker-compose-simple.yml logs -f

# 로컬 실행 시 터미널에 직접 출력
```

### 데이터베이스 접속
```bash
# Docker PostgreSQL 접속
docker exec -it meari-postgres psql -U meari_user -d meari_db

# 테이블 확인
\dt

# 데이터 개수 확인
SELECT COUNT(*) FROM news;  -- 887개
SELECT COUNT(*) FROM youth_policies;  -- 3,977개
```

### 테스트 실행
```bash
# 단일 사용자 테스트
curl -X POST http://localhost:8000/api/v1/meari/sessions \
  -H "Content-Type: application/json" \
  -d '{"selected_tag_id": 1}'

# 동시 사용자 테스트
./test_concurrent3.sh
```

## 지원

문제 발생 시:
1. 이 README의 트러블슈팅 섹션 확인
2. 팀 슬랙 채널에 문의
3. 프로젝트 리더에게 직접 연락

## 라이센스

This project is proprietary and confidential.

---

**Note**: 
- `.env` 파일과 `meari_db_dump.sql`은 절대 Git에 커밋하지 마세요!
- 개발 시 docker-compose-simple.yml 사용 권장
- 성능 테스트 시에만 docker-compose.yml (6 인스턴스) 사용