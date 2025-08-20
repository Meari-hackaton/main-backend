# 메아리 백엔드 팀원 설정 가이드

## 🎯 목표
3분 안에 메아리 백엔드를 실행하고 API 테스트하기

## ✅ 체크리스트

### 1. 필수 파일 받기 (팀 리더에게 요청)
- [ ] `.env` 파일 - API 키와 클라우드 DB 연결 정보
- [ ] `meari_db_dump.sql` 파일 - PostgreSQL 데이터 (7.2MB)

### 2. Docker Desktop 설치
- [ ] [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/)
- [ ] 설치 후 Docker Desktop 실행

### 3. 코드 받기 및 실행
```bash
# 1. 저장소 클론
git clone https://github.com/your-org/meari-backend.git
cd meari-backend

# 2. 받은 파일들 복사
# .env 파일을 프로젝트 루트에 복사
# meari_db_dump.sql 파일을 프로젝트 루트에 복사

# 3. Docker Compose 실행
docker-compose -f docker-compose-simple.yml up
```

### 4. 작동 확인
- [ ] http://localhost:8000/docs 접속
- [ ] Swagger UI가 표시되는지 확인

## 🚫 하지 말아야 할 것들

### 절대 하지 마세요:
- ❌ PostgreSQL 로컬 설치 (Docker가 자동 처리)
- ❌ Neo4j 로컬 설치 (클라우드 사용)
- ❌ Milvus 로컬 설치 (클라우드 사용)
- ❌ `scripts/collect_*.py` 실행 (데이터 이미 수집됨)
- ❌ `.env` 파일 Git에 커밋

### 이미 준비된 것들:
- ✅ PostgreSQL 데이터: 887개 뉴스, 3,977개 정책
- ✅ Milvus 벡터: 877개 인용문, 3,977개 정책
- ✅ Neo4j 그래프: 5,262개 노드, 15,257개 관계

## 🆘 문제 해결

### Docker 실행 오류
```bash
# 기존 컨테이너 정리
docker-compose -f docker-compose-simple.yml down

# 볼륨까지 완전 삭제 (데이터 초기화)
docker-compose -f docker-compose-simple.yml down -v

# 다시 실행
docker-compose -f docker-compose-simple.yml up
```

### 포트 충돌 (5432 already in use)
```bash
# 로컬 PostgreSQL 중지
sudo systemctl stop postgresql  # Linux
brew services stop postgresql   # macOS

# 또는 포트 변경 (docker-compose-simple.yml 수정)
ports:
  - "5433:5432"  # 5433으로 변경
```

### 메모리 부족
Docker Desktop → Settings → Resources → Memory를 4GB 이상으로 설정

## 📊 시스템 구조

```
[프론트엔드] 
    ↓
[FastAPI (localhost:8000)]
    ↓
[PostgreSQL (Docker)] + [Neo4j (Cloud)] + [Milvus (Cloud)]
    ↓
[Gemini API]
```

## 🧪 API 테스트

### 1. Swagger UI 사용 (권장)
http://localhost:8000/docs 에서 직접 테스트

### 2. curl 사용
```bash
# 세션 생성 테스트
curl -X POST http://localhost:8000/api/v1/meari/sessions \
  -H "Content-Type: application/json" \
  -H "Cookie: session=test-user-1" \
  -d '{"selected_tag_id": 1, "user_context": "테스트"}'
```

### 3. 응답 시간
- 첫 요청: 30-60초 (정상 - AI 처리 시간)
- 이후 요청: 20-40초

## 📝 개발 팁

### 로그 보기
```bash
# 실시간 로그
docker-compose -f docker-compose-simple.yml logs -f

# 앱 로그만
docker-compose -f docker-compose-simple.yml logs -f app
```

### DB 데이터 확인
```bash
# PostgreSQL 접속
docker exec -it meari-postgres psql -U meari_user -d meari_db

# 데이터 개수 확인
SELECT COUNT(*) FROM news;           # 887
SELECT COUNT(*) FROM youth_policies;  # 3,977
SELECT COUNT(*) FROM news_quotes;     # 877
\q  # 종료
```

### 서버 재시작
```bash
# 컨테이너 재시작
docker-compose -f docker-compose-simple.yml restart app

# 완전 재시작
docker-compose -f docker-compose-simple.yml down
docker-compose -f docker-compose-simple.yml up
```

## 🔄 Git 작업 흐름

```bash
# 최신 코드 받기
git pull origin main

# 브랜치 생성
git checkout -b feature/your-feature

# 작업 후 커밋
git add .
git commit -m "feat: 기능 설명"

# 푸시 전 .env 체크!
git status  # .env가 없는지 확인

git push origin feature/your-feature
```

## 💡 자주 묻는 질문

**Q: psql이 없다고 나와요**
A: Docker를 사용하세요. psql 설치 불필요.

**Q: Neo4j 설치해야 하나요?**
A: 아니요. 클라우드 사용. .env만 있으면 됨.

**Q: 데이터 수집 스크립트 실행해야 하나요?**
A: 아니요. 이미 완료됨. 실행하지 마세요.

**Q: Python 가상환경 필요한가요?**
A: Docker 사용 시 불필요. 로컬 개발 시에만 필요.

**Q: 동시에 몇 명까지 테스트 가능한가요?**
A: docker-compose-simple.yml: 3-5명
A: docker-compose.yml: 30명 (테스트용)

---

**도움 필요 시**: 슬랙 채널 또는 팀 리더에게 문의