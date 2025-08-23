# 🚀 EC2 배포 가이드

## 📋 배포 전 체크리스트

### 백엔드 EC2 정보
- **인스턴스**: t3.small
- **주소**: ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com
- **포트**: 8000

### 프론트엔드 EC2 정보
- **인스턴스**: t2.small
- **주소**: ec2-43-200-4-71.ap-northeast-2.compute.amazonaws.com
- **포트**: 3000 (또는 80)

## 🔧 백엔드 배포 방법

### 1. EC2 접속
```bash
ssh -i your-key.pem ubuntu@ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com
```

### 2. 필요 파일 업로드 (중요!)
```bash
# 데이터베이스 덤프 파일 업로드
scp -i your-key.pem meari_db_dump.sql ubuntu@ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:/home/ubuntu/meari-backend/

# User 테이블 업데이트 스크립트도 업로드 (자체 로그인용)
scp -i your-key.pem scripts/update_user_table.py ubuntu@ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:/home/ubuntu/meari-backend/scripts/
```

### 3. 자동 배포 스크립트 실행
```bash
# 프로젝트 디렉토리로 이동
cd /home/ubuntu/meari-backend

# 스크립트 다운로드
wget https://raw.githubusercontent.com/Meari-hackaton/main-backend/sosang/deploy_ec2_final.sh

# 실행 권한 부여
chmod +x deploy_ec2_final.sh

# 배포 실행
./deploy_ec2_final.sh
```

### 4. 수동 배포 (문제 발생 시)

#### Step 1: 코드 가져오기
```bash
cd /home/ubuntu
git clone https://github.com/Meari-hackaton/main-backend.git meari-backend
cd meari-backend
git checkout sosang
```

#### Step 2: Python 환경 설정
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 3: 환경변수 설정 (.env 파일)
```bash
nano .env
```

최소 필요 환경변수:
```env
DATABASE_URL=postgresql+asyncpg://meari_user:meari_password@localhost/meari_db
SECRET_KEY=your-secret-key-here
SESSION_COOKIE_NAME=meari_session
SESSION_EXPIRES_DAYS=7
GEMINI_API_KEY=your-api-key
BIGKINDS_ACCESS_KEY=your-api-key
```

#### Step 4: DB 복구 또는 초기화
```bash
# 덤프 파일이 있는 경우
PGPASSWORD=meari_password psql -h localhost -U meari_user -d meari_db < meari_db_dump.sql

# 덤프 파일이 없는 경우 (빈 DB로 시작)
python -m app.db.init_db
python -m app.db.seed_tags
```

#### Step 5: 서버 실행
```bash
# 개발 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션 모드 (백그라운드)
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

## 🔍 배포 확인

### 1. 헬스체크
```bash
curl http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000/health
```

### 2. API 문서
브라우저에서 접속:
```
http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000/docs
```

### 3. 로그 확인
```bash
# systemd 사용 시
sudo journalctl -u meari-backend -f

# nohup 사용 시
tail -f app.log
```

## 🔌 프론트엔드 연동

프론트엔드 .env 파일:
```env
REACT_APP_API_URL=http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000
```

## ⚠️ 트러블슈팅

### PostgreSQL 연결 실패
```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# 데이터베이스 생성
sudo -u postgres psql
CREATE DATABASE meari_db;
CREATE USER meari_user WITH PASSWORD 'password';
GRANT ALL ON DATABASE meari_db TO meari_user;
\q
```

### 포트 8000 접근 불가
```bash
# 보안 그룹에서 8000 포트 열기 (AWS 콘솔)
# 또는 방화벽 설정
sudo ufw allow 8000
```

### 서비스 재시작
```bash
# systemd 사용 시
sudo systemctl restart meari-backend

# 프로세스 직접 관리 시
ps aux | grep uvicorn
kill -9 [PID]
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

## 📝 업데이트 방법

```bash
cd /home/ubuntu/meari-backend
git pull origin sosang
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart meari-backend
```

## 🎯 테스트 API 호출

### 회원가입 테스트
```bash
curl -X POST http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "nickname": "테스트유저"
  }'
```

### 로그인 테스트
```bash
curl -X POST http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

---

**문의사항이 있으시면 언제든 연락주세요!** 🙌