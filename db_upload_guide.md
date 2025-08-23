# 📦 데이터베이스 덤프 파일 업로드 가이드

## 파일 정보
- **파일명**: `meari_db_dump.sql` (6.9MB)
- **내용**: 뉴스 887개, 인용문 877개, 정책 3,977개, 태그 9개

## 업로드 방법

### 1. 로컬에서 EC2로 직접 업로드
```bash
# 현재 디렉토리에 meari_db_dump.sql이 있는 경우
scp -i your-key.pem meari_db_dump.sql ubuntu@ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:/home/ubuntu/

# 업로드 후 EC2에서 이동
ssh -i your-key.pem ubuntu@ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com
sudo mv /home/ubuntu/meari_db_dump.sql /home/ubuntu/meari-backend/
```

### 2. GitHub 릴리즈 활용 (대용량 파일)
```bash
# GitHub 릴리즈에 업로드 후 EC2에서 다운로드
cd /home/ubuntu/meari-backend
wget https://github.com/Meari-hackaton/main-backend/releases/download/v1.0/meari_db_dump.sql
```

### 3. S3 활용 (AWS 사용시)
```bash
# S3에 업로드 후 EC2에서 다운로드
aws s3 cp s3://your-bucket/meari_db_dump.sql ./
```

## 복구 확인
```bash
# PostgreSQL 접속해서 데이터 확인
psql -h localhost -U meari_user -d meari_db

# 테이블 목록 확인
\dt

# 데이터 개수 확인
SELECT COUNT(*) FROM news;
SELECT COUNT(*) FROM news_quotes;
SELECT COUNT(*) FROM youth_policies;
SELECT COUNT(*) FROM tags;

# 종료
\q
```

## 주의사항
- 덤프 파일이 없으면 빈 DB로 시작되며, 모든 데이터를 다시 수집해야 합니다
- 덤프 파일 업로드 전에 배포 스크립트를 실행하면 빈 DB가 생성됩니다
- 이미 배포했다면 덤프 파일 업로드 후 수동으로 복구 가능합니다