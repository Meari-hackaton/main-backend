# 메아리(Meari) API 명세서

## 🔗 Base URL
- Development (로컬): `http://localhost:8001`
- Development (Docker): `http://localhost:8000`
- Production: `https://api.meari.com` (TBD)

## 🔑 인증
- Cookie 기반 세션 인증
- Cookie Name: `session`
- 모든 API 요청에 세션 쿠키 필요

---

## 📋 API 엔드포인트

### 1. 메아리 세션 API

#### 1.1 초기 세션 생성
공감 카드, 성찰 카드, 초기 페르소나를 생성합니다.

**Endpoint:** `POST /api/v1/meari/sessions`

**Request Body:**
```json
{
  "selected_tag_id": 2,  // 중분류 태그 ID (2-12)
  "user_context": "매일 야근하고 주말에도 일해야 해서 너무 지쳐있어요..."  // 선택사항, 최대 500자
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "session_type": "initial",
  "timestamp": "2024-01-01T00:00:00Z",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "cards": {
    "empathy": {
      "type": "empathy",
      "title": "당신의 마음을 이해해요",
      "content": "매일 야근과 주말 근무로 지쳐있는 당신의 마음이 충분히 이해됩니다...",
      "quotes_used": [
        {
          "quote": "일과 삶의 균형이 무너지면 삶 자체가 일이 됩니다",
          "speaker": "김미경",
          "news_id": "NEWS123"
        }
      ],
      "emotion_keywords": ["번아웃", "지침", "불안"]
    },
    "reflection": {
      "type": "reflection",
      "title": "당신은 혼자가 아니에요",
      "content": "많은 청년들이 당신과 같은 고민을 하고 있습니다...",
      "insights": {
        "problem": "만성적 과로로 인한 번아웃",
        "causes": ["과도한 업무량", "일과 삶의 불균형", "휴식 부족"],
        "solutions": ["업무 경계 설정", "정기적 휴식", "스트레스 관리"],
        "supporters": ["고용노동부", "청년재단", "정신건강복지센터"],
        "peers": ["20-30대 직장인", "IT 업계 종사자"]
      },
      "key_message": "번아웃은 개인의 문제가 아닌 구조적 문제입니다"
    }
  },
  "persona": {
    "depth": "surface",
    "depth_label": "초기 이해",
    "summary": "과로로 지친 청년 직장인",
    "characteristics": ["책임감이 강함", "완벽주의 성향", "번아웃 상태"],
    "needs": ["충분한 휴식", "업무 경계 설정", "정서적 지지"],
    "growth_direction": "일과 삶의 균형 회복"
  },
  "next_action": "growth_content"
}
```

**응답 시간:** 30-60초 (AI 처리 시간)

---

#### 1.2 성장 콘텐츠 생성
정보, 경험, 지원 3종 카드를 생성합니다.

**Endpoint:** `POST /api/v1/meari/growth-contents`

**Request Body:**
```json
{
  "context": "initial",  // "initial" 또는 "ritual"
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "persona_summary": "번아웃으로 지친 청년 직장인",  // 선택사항
  "previous_policy_ids": ["POL001", "POL002"]  // 중복 방지용
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "content_type": "growth",
  "timestamp": "2024-01-01T00:00:00Z",
  "cards": {
    "information": {
      "type": "information",
      "title": "번아웃 극복을 위한 실질적 방법",
      "search_query": "직장인 번아웃 극복 방법",
      "summary": "전문가들은 번아웃 극복을 위해 다음을 권장합니다...",
      "sources": [
        "한국직업건강간호학회지",
        "서울대학교 행복연구센터"
      ]
    },
    "experience": {
      "type": "experience",
      "title": "5분 호흡 명상",
      "activity": "편안한 자세로 앉아 천천히 호흡하며...",
      "duration": "5분",
      "difficulty": "쉬움"
    },
    "support": {
      "type": "support",
      "title": "청년 마음건강 지원사업",
      "policy_name": "청년 마음건강 바우처",
      "description": "전문 심리상담 10회 무료 지원...",
      "organization": "보건복지부",
      "application_url": "https://..."
    }
  }
}
```

**응답 시간:** 20-40초

---

#### 1.3 리츄얼 기록
일일 리츄얼 완료를 기록하고 페르소나를 업데이트합니다.

**Endpoint:** `POST /api/v1/meari/rituals`

**Request Body:**
```json
{
  "diary_entry": "오늘은 추천받은 명상을 시도해봤어요. 생각보다 마음이 편안해졌습니다.",
  "selected_mood": "hopeful",  // hopeful, calm, tired, anxious 등
  "growth_contents_viewed": ["card_001", "card_002"]  // 본 콘텐츠 ID
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "action": "ritual_recorded",
  "timestamp": "2024-01-01T00:00:00Z",
  "ritual_id": 1,
  "persona": {
    "updated": true,
    "depth": "understanding",
    "depth_label": "깊어진 이해",
    "summary": "회복을 시도하는 청년 직장인",
    "changes": ["명상에 대한 긍정적 경험 추가"]
  },
  "tree": {
    "stage": "sprouting",
    "stage_label": "새싹",
    "progress": 7,
    "next_milestone": 14,
    "percentage": 25.0
  },
  "message": "7일째 함께하고 있어요. 마음나무가 새싹을 틔웠습니다!",
  "next_growth_content": null  // 또는 새로운 성장 콘텐츠
}
```

---

### 2. 대시보드 API

#### 2.1 대시보드 메인
전체 현황을 조회합니다.

**Endpoint:** `GET /api/v1/dashboard/`

**Response (200 OK):**
```json
{
  "tree": {
    "level": 7,
    "stage": "sprouting",
    "stage_label": "새싹",
    "next_milestone": 14,
    "percentage": 25.0
  },
  "statistics": {
    "continuous_days": 7,
    "total_rituals": 15,
    "practiced_rituals": 8,
    "monthly_completed": 7
  },
  "today_ritual": {
    "id": 123,
    "title": "10분 명상하기",
    "is_completed": false,
    "type": "meditation"
  },
  "notifications": [
    {
      "type": "reminder",
      "message": "'10분 명상하기' 리츄얼이 기다리고 있어요",
      "icon": "clock"
    }
  ]
}
```

---

#### 2.2 캘린더 조회
월별 리츄얼 완료 현황을 조회합니다.

**Endpoint:** `GET /api/v1/dashboard/calendar?year=2024&month=5`

**Query Parameters:**
- `year`: 연도 (필수)
- `month`: 월 (필수, 1-12)

**Response (200 OK):**
```json
{
  "year": 2024,
  "month": 5,
  "days": [
    {
      "date": "2024-05-01",
      "has_ritual": true,
      "is_completed": true,
      "ritual_id": 1,
      "ritual_title": "아침 요가",
      "ritual_type": "exercise",
      "user_mood": "energetic"
    }
  ],
  "summary": {
    "total_days": 31,
    "completed_days": 15,
    "completion_rate": 48.4,
    "current_streak": 7
  }
}
```

---

#### 2.3 일일 리츄얼 생성
오늘의 리츄얼을 생성합니다.

**Endpoint:** `POST /api/v1/dashboard/rituals`

**Request Body:**
```json
{
  "title": "10분 명상하기",
  "description": "조용한 곳에서 호흡에 집중하며 마음을 가라앉히세요",
  "type": "meditation",  // meditation, exercise, diary, etc.
  "duration_minutes": 10  // 1-60
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "date": "2024-05-01",
  "title": "10분 명상하기",
  "description": "조용한 곳에서 호흡에 집중하며...",
  "type": "meditation",
  "duration_minutes": 10,
  "is_completed": false,
  "completed_at": null,
  "user_note": null,
  "user_mood": null,
  "difficulty_rating": null
}
```

---

#### 2.4 리츄얼 완료 처리
리츄얼을 완료 처리합니다.

**Endpoint:** `PATCH /api/v1/dashboard/rituals/{id}/complete`

**Path Parameters:**
- `id`: 리츄얼 ID

**Request Body (Optional):**
```json
{
  "user_note": "명상 후 마음이 많이 편안해졌어요",
  "user_mood": "calm",
  "difficulty_rating": 2  // 1-5
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "date": "2024-05-01",
  "title": "10분 명상하기",
  "is_completed": true,
  "completed_at": "2024-05-01T09:30:00Z",
  "user_note": "명상 후 마음이 많이 편안해졌어요",
  "user_mood": "calm",
  "difficulty_rating": 2
}
```

---

#### 2.5 연속 기록 조회
활동 연속 기록을 조회합니다.

**Endpoint:** `GET /api/v1/dashboard/streak`

**Response (200 OK):**
```json
{
  "current_streak": 7,
  "longest_streak": 21,
  "total_days_active": 45,
  "total_rituals_completed": 50,
  "total_rituals_created": 52,
  "last_activity_date": "2024-05-01"
}
```

---

### 3. 사용자 이력 API

#### 3.1 콘텐츠 이력 조회
본 콘텐츠 이력을 조회합니다.

**Endpoint:** `GET /api/v1/history/contents`

**Query Parameters:**
- `content_type`: 콘텐츠 타입 (policy, news, etc.) - 선택사항
- `limit`: 조회 개수 (기본값: 50)

**Response (200 OK):**
```json
{
  "contents": [
    {
      "content_type": "policy",
      "content_id": "POL001",
      "viewed_at": "2024-05-01T10:00:00Z",
      "title": "청년 마음건강 바우처"
    }
  ],
  "total_count": 25
}
```

---

## 📊 데이터 구조

### 태그 ID 매핑
```
대분류 (parent_id):
1: 진로/취업
2: 마음/건강  
3: 인간관계

중분류 (id):
2: 직장 내 번아웃 (진로/취업)
3: 취업 불안/스트레스 (진로/취업)
4: 이직/커리어 전환 (진로/취업)
5: 우울감/무기력 (마음/건강)
6: 건강염려증 (마음/건강)
7: 수면장애 (마음/건강)
8: 가족 갈등 (인간관계)
9: 사회적 고립감 (인간관계)
10: 세대 갈등 (인간관계)
```

### 마음나무 단계
```
progress → stage:
0-6: seed (씨앗)
7-13: sprouting (새싹)
14-20: growing (성장)
21-27: blooming (개화)
28+: full_bloom (만개)
```

### 페르소나 깊이
```
depth levels:
- surface: 표면적 이해
- understanding: 깊어진 이해
- insight: 통찰
- deep_insight: 깊은 통찰
- wisdom: 지혜
```

---

## ⚠️ 중요 사항

### 응답 시간
- 초기 세션: 30-60초 (공감 + 성찰 + 페르소나)
- 성장 콘텐츠: 20-40초 (3종 카드)
- 리츄얼 기록: 5-10초
- 대시보드 조회: < 1초

### 동시 사용자 제한
- 단일 인스턴스: 3-5명
- Docker Compose (6 인스턴스): 30명
- Gemini API 제한: 분당 10 요청

### 에러 처리
모든 에러는 다음 형식으로 반환:
```json
{
  "status": "error",
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "요청한 리소스를 찾을 수 없습니다",
  "detail": "Session ID: 123e4567...",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### HTTP 상태 코드
- 200: 성공 (조회)
- 201: 성공 (생성)
- 400: 잘못된 요청
- 401: 인증 필요
- 404: 리소스 없음
- 429: 요청 제한 초과
- 500: 서버 오류

---

## 🧪 테스트

### Swagger UI
- 로컬: http://localhost:8001/docs
- Docker: http://localhost:8000/docs

### curl 예시
```bash
# 세션 생성 (로컬)
curl -X POST http://localhost:8001/api/v1/meari/sessions \
  -H "Content-Type: application/json" \
  -H "Cookie: session=test-user-1" \
  -d '{"selected_tag_id": 2}'

# 대시보드 조회 (로컬)
curl -X GET http://localhost:8001/api/v1/dashboard/ \
  -H "Cookie: session=test-user-1"
```

---

## 📞 문의
- Slack: #meari-dev
- Email: dev@meari.com