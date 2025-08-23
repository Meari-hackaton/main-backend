# 🔄 프론트엔드 인증 시스템 변경 가이드

## 📌 변경사항 요약
- Google OAuth 제거 → 이메일/비밀번호 로그인으로 변경
- EC2 HTTP 환경에서 즉시 배포 가능
- 세션 기반 인증 (쿠키 사용)

## 🔗 백엔드 API 엔드포인트

### Backend URL
```
개발: http://localhost:8000
배포: http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000
```

### 인증 API

#### 1. 회원가입
```javascript
POST /api/v1/auth/signup
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "password123",
  "nickname": "사용자닉네임"
}

Response (201):
{
  "id": "uuid",
  "email": "user@example.com",
  "nickname": "사용자닉네임",
  "message": "회원가입이 완료되었습니다"
}
```

#### 2. 로그인
```javascript
POST /api/v1/auth/login
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "password123"
}

Response (200):
{
  "id": "uuid",
  "email": "user@example.com",
  "nickname": "사용자닉네임",
  "message": "로그인 성공"
}
```

#### 3. 로그아웃
```javascript
POST /api/v1/auth/logout

Response (200):
{
  "message": "로그아웃 성공"
}
```

#### 4. 인증 상태 확인
```javascript
GET /api/v1/auth/check

Response (200):
{
  "authenticated": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "nickname": "사용자닉네임"
  }
}

// 또는 미인증 상태
{
  "authenticated": false
}
```

#### 5. 현재 사용자 정보 (기존 유지)
```javascript
GET /api/v1/auth/me

Response (200):
{
  "id": "uuid",
  "email": "user@example.com",
  "nickname": "사용자닉네임",
  "social_provider": null,
  "created_at": "2025-08-23T..."
}
```

## 🎯 프론트엔드 수정 사항

### 1. axios 설정 (withCredentials 필수!)
```javascript
// services/api.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,  // 쿠키 자동 전송 (필수!)
  headers: {
    'Content-Type': 'application/json',
  }
});

export default api;
```

### 2. 로그인 페이지 변경
```javascript
// pages/LoginPage.jsx
import React, { useState } from 'react';
import api from '../services/api';

function LoginPage() {
  const [isSignup, setIsSignup] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    nickname: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const endpoint = isSignup ? '/api/v1/auth/signup' : '/api/v1/auth/login';
      const response = await api.post(endpoint, formData);
      
      if (response.status === 200 || response.status === 201) {
        // 로그인/회원가입 성공
        if (isSignup) {
          // 회원가입 후 온보딩으로
          window.location.href = '/steps';
        } else {
          // 로그인 후 대시보드로
          window.location.href = '/dashboard';
        }
      }
    } catch (error) {
      alert(error.response?.data?.detail || '오류가 발생했습니다');
    }
  };

  return (
    <div>
      <h2>{isSignup ? '회원가입' : '로그인'}</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="이메일"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
        <input
          type="password"
          placeholder="비밀번호"
          value={formData.password}
          onChange={(e) => setFormData({...formData, password: e.target.value})}
          required
        />
        {isSignup && (
          <input
            type="text"
            placeholder="닉네임"
            value={formData.nickname}
            onChange={(e) => setFormData({...formData, nickname: e.target.value})}
            required
          />
        )}
        <button type="submit">
          {isSignup ? '회원가입' : '로그인'}
        </button>
      </form>
      <button onClick={() => setIsSignup(!isSignup)}>
        {isSignup ? '로그인으로' : '회원가입으로'}
      </button>
    </div>
  );
}
```

### 3. 인증 체크 (Protected Routes)
```javascript
// components/ProtectedRoute.jsx
import { useEffect, useState } from 'react';
import api from '../services/api';

function ProtectedRoute({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await api.get('/api/v1/auth/check');
      setIsAuthenticated(response.data.authenticated);
    } catch (error) {
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) return <div>Loading...</div>;
  if (!isAuthenticated) {
    window.location.href = '/login';
    return null;
  }

  return children;
}
```

### 4. 로그아웃 처리
```javascript
const handleLogout = async () => {
  try {
    await api.post('/api/v1/auth/logout');
    window.location.href = '/login';
  } catch (error) {
    console.error('Logout failed:', error);
  }
};
```

## 🚨 중요 체크리스트

### ✅ 필수 확인사항
- [ ] **withCredentials: true** 설정 (axios)
- [ ] Google OAuth 관련 코드 모두 제거
- [ ] 로그인/회원가입 폼 구현
- [ ] 인증 상태 체크 로직 변경
- [ ] 환경변수 업데이트

### 환경변수 설정 (.env)
```bash
# 개발
REACT_APP_API_URL=http://localhost:8000

# 배포 (EC2)
REACT_APP_API_URL=http://ec2-13-125-128-95.ap-northeast-2.compute.amazonaws.com:8000
```

## 🔄 마이그레이션 순서

1. **로그인 페이지 먼저 변경** (OAuth 버튼 → 폼으로)
2. **API 서비스 수정** (withCredentials 추가)
3. **인증 체크 로직 변경** (/auth/check 사용)
4. **테스트 후 배포**

## 📱 테스트 시나리오

1. 회원가입 → 온보딩(steps) 이동 확인
2. 로그인 → 대시보드 이동 확인
3. 새로고침 후 세션 유지 확인
4. 로그아웃 → 로그인 페이지 이동 확인
5. 미인증 상태에서 보호된 페이지 접근 시 리다이렉트 확인

## 🆘 문제 발생 시

### CORS 에러
- withCredentials: true 확인
- 백엔드 CORS 설정에 프론트엔드 도메인 포함 확인

### 쿠키가 저장되지 않음
- HTTP 환경이므로 secure: false 확인 (백엔드)
- SameSite: 'lax' 설정 확인

### 세션이 유지되지 않음
- 모든 API 호출에 withCredentials: true 설정
- 쿠키 이름: meari_session 확인

---

**백엔드 담당자 연락처**: 필요시 즉시 수정 가능합니다!