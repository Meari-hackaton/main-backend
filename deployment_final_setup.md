# 메아리 백엔드 최종 배포 설정 가이드

## 현재 상태
- ✅ EC2 백엔드: http://54.180.124.90:8000
- ✅ Cloudflare Tunnel HTTPS: 생성 필요
- ✅ 프론트엔드: https://meari-seven.vercel.app
- ✅ PostgreSQL: Railway (외부)
- ✅ Milvus/Neo4j: Cloud 서비스

## 1. Cloudflare Tunnel 설정 (HTTPS 제공)

### 로컬에서 Cloudflare Tunnel 실행
```bash
# Mac에서 실행 (EC2 아님!)
cloudflared tunnel --url http://54.180.124.90:8000
```

생성된 HTTPS URL 예시:
- https://[random-subdomain].trycloudflare.com

## 2. Google OAuth 설정 업데이트

[Google Cloud Console](https://console.cloud.google.com/apis/credentials) 접속

### OAuth 2.0 클라이언트 수정
승인된 리디렉션 URI 추가:
```
https://[cloudflare-url]/auth/google/callback
```

## 3. 프론트엔드 환경변수 업데이트

### Vercel 대시보드에서:
1. Settings → Environment Variables
2. REACT_APP_API_URL 수정:
```
REACT_APP_API_URL=https://[cloudflare-url]
```
3. Redeploy 트리거

## 4. 백엔드 .env 업데이트 (EC2)

```bash
ssh -i ~/Downloads/meari-backend-key.pem ubuntu@54.180.124.90
cd meari-backend
nano .env
```

수정할 항목:
```env
BACKEND_URL=https://[cloudflare-url]
FRONTEND_URL=https://meari-seven.vercel.app
```

서버 재시작:
```bash
sudo systemctl restart meari-backend
# 또는
pm2 restart meari-backend
```

## 5. 테스트 체크리스트

### API 테스트
- [ ] https://[cloudflare-url]/docs 접속 확인
- [ ] CORS 에러 없는지 확인

### OAuth 플로우 테스트
- [ ] https://meari-seven.vercel.app 접속
- [ ] Google 로그인 클릭
- [ ] Google 계정 선택
- [ ] 리디렉션 성공 확인
- [ ] 온보딩/대시보드 진입 확인

### 주요 기능 테스트
- [ ] 태그 선택 (온보딩)
- [ ] 공감/성찰 카드 생성
- [ ] 성장 콘텐츠 표시
- [ ] 리츄얼 생성/완료
- [ ] 대시보드 마음나무 표시

## 6. 트러블슈팅

### CORS 에러 발생 시
EC2 백엔드 main.py 확인:
```python
allow_origins=[
    "https://meari-seven.vercel.app",
    "http://localhost:3000"
]
```

### OAuth 리디렉션 실패 시
1. Google Console에서 Redirect URI 확인
2. 백엔드 BACKEND_URL 환경변수 확인
3. secure=True 설정 확인 (HTTPS인 경우)

### Mixed Content 에러
- 모든 API 호출이 HTTPS로 되는지 확인
- 프론트엔드 환경변수 재배포 확인

## 7. 해커톤 운영 가이드

### 월요일 체크리스트
- [ ] Cloudflare Tunnel 실행 상태 유지
- [ ] EC2 인스턴스 모니터링
- [ ] 에러 로그 확인: `pm2 logs`
- [ ] DB 연결 상태 확인

### 예상 사용량
- 사용자: 10-20명
- 동시 접속: 5-10명
- API 호출: 시간당 100-200회
- AI 처리: 분당 2-3회

### 긴급 대응
```bash
# 서버 재시작
ssh -i ~/key.pem ubuntu@54.180.124.90
pm2 restart all

# 로그 확인
pm2 logs --lines 100

# 메모리 확인
free -h
htop
```

## 8. 배포 완료 후 확인사항

✅ 체크리스트:
- [ ] HTTPS URL로 API 접속 가능
- [ ] OAuth 로그인 정상 작동
- [ ] 프론트-백엔드 통신 정상
- [ ] 모든 주요 기능 테스트 완료
- [ ] 에러 로그 클린
- [ ] 성능 테스트 (응답시간 체크)

---

**중요**: Cloudflare Tunnel은 터미널 세션 유지 필요
- tmux 또는 screen 사용 권장
- 또는 백그라운드 실행: `nohup cloudflared tunnel --url http://54.180.124.90:8000 &`