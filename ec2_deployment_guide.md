# EC2 배포 가이드 (PostgreSQL 포함)

## 1. EC2 인스턴스 사양 재설정

### 권장 인스턴스 타입: **t3.medium**
- vCPU: 2
- Memory: 4 GiB
- Storage: 30 GiB (DB 데이터 포함)
- 예상 비용: 약 $0.0416/시간 (월 $30)

### 이유:
- PostgreSQL 서버 실행 (1GB RAM)
- FastAPI 백엔드 (1GB RAM)
- Nginx, PM2 등 (0.5GB RAM)
- 20명 동시 접속 처리 (1.5GB RAM)

## 2. EC2 인스턴스 생성

### Step 1: AMI 선택
- Ubuntu Server 24.04 LTS (현재 선택된 것 유지)

### Step 2: Instance Type
- **t3.medium** 선택 ⚠️ (t2.small 아님)

### Step 3: Key Pair
- Create new key pair
- Name: `meari-backend-key`
- Type: RSA
- Format: .pem

### Step 4: Network Settings
Security Group Rules:
```
Type        | Port Range | Source
------------|------------|-------------
SSH         | 22         | My IP
HTTP        | 80         | 0.0.0.0/0
HTTPS       | 443        | 0.0.0.0/0
Custom TCP  | 8000       | 0.0.0.0/0
PostgreSQL  | 5432       | My IP (보안용)
```

### Step 5: Storage
- **30 GiB** gp3 (기본 8GB에서 변경)
- IOPS: 3000 (기본값)
- Throughput: 125 MB/s (기본값)

### Step 6: Launch
- Launch instance 클릭

## 3. 인스턴스 설정 후 할 일

### 3.1 Elastic IP 할당 (권장)
- EC2 Dashboard → Elastic IPs
- Allocate Elastic IP address
- Associate with instance
- 고정 IP로 OAuth 설정 가능

### 3.2 인스턴스 접속 테스트
```bash
# 키 파일 권한 설정
chmod 400 ~/Downloads/meari-backend-key.pem

# SSH 접속
ssh -i ~/Downloads/meari-backend-key.pem ubuntu@<EC2_PUBLIC_IP>
```

## 4. 서버 구성 예상

### 포함되는 것:
- PostgreSQL 15 (로컬 DB)
- FastAPI 백엔드
- Nginx (리버스 프록시)
- PM2 (프로세스 관리)
- 878개 인용문 데이터
- 1,137개 뉴스 데이터
- 3,977개 정책 데이터
- 모든 태그 데이터

### 외부 서비스 (유지):
- Milvus (Zilliz Cloud) - 벡터 검색
- Neo4j (Aura) - 그래프 DB
- Gemini API - AI 처리

## 5. 예상 성능

### t3.medium 스펙으로:
- 동시 접속: 20-30명
- API 응답: 평균 500ms
- AI 처리: 8-10초 (Gemini API 의존)
- DB 쿼리: 50ms 이하
- 메모리 여유: 약 1GB

## 6. 비용 예상 (1주일 해커톤)

### EC2 t3.medium
- 시간당: $0.0416
- 일일: $1.00
- 1주일: $7.00

### Elastic IP (할당만 하고 미사용 시)
- 무료 (인스턴스에 연결 시)

### 데이터 전송
- 인바운드: 무료
- 아웃바운드: 100GB까지 무료 티어

### 총 예상 비용: $7-10 (1주일)

## 7. 다음 단계

EC2 생성 화면에서:
1. Instance type을 **t3.medium**으로 변경
2. Storage를 **30 GiB**로 변경
3. Security Group에 PostgreSQL 포트 추가
4. Launch instance

인스턴스 생성 후 Public IP 알려주시면 자동 배포 스크립트 실행하겠습니다.