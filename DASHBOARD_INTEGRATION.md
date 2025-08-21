# 성장 콘텐츠 ↔ 대시보드 연동 설명서

## 📊 현재 데이터 흐름

### 1. 성장 콘텐츠 생성 시 (POST /api/meari/growth-contents)
```
사용자 요청 
→ GrowthAgent 실행 (3종 콘텐츠 생성)
→ GeneratedCard 테이블 저장 (information, experience, support)
→ DailyRitual 테이블 저장 (experience만, ritual_type='growth_experience')
```

### 2. 데이터 저장 구조

#### GeneratedCard 테이블
- 모든 AI 생성 카드 저장
- card_type: empathy, reflection, growth
- sub_type: information, experience, support
- 히스토리 추적용

#### DailyRitual 테이블  
- 대시보드에 표시되는 일일 리츄얼
- experience 카드가 자동으로 여기에도 저장됨
- ritual_type='growth_experience'로 구분
- 사용자가 완료 처리 가능

#### UserStreak & HeartTree
- 리츄얼 완료 시 자동 업데이트
- 연속 기록 및 마음나무 성장

## 🔄 전체 플로우

### Step 1: 메아리 세션 생성
```http
POST /api/meari/sessions
{
  "selected_tag_id": 1,
  "user_context": "매일 야근으로 번아웃 상태입니다"
}
```
- 공감/성찰 카드 생성
- 초기 페르소나 생성
- session_id 반환

### Step 2: 성장 콘텐츠 생성
```http
POST /api/meari/growth-contents
{
  "session_id": "uuid-here",
  "context": "initial",
  "previous_policy_ids": []
}
```
- 3종 콘텐츠 생성 (정보/경험/지원)
- **experience 카드 → DailyRitual 자동 저장** ✨

### Step 3: 대시보드 조회
```http
GET /api/dashboard/
```
응답:
```json
{
  "today_ritual": {
    "id": 123,
    "title": "10분 마음챙김 명상",
    "is_completed": false,
    "type": "growth_experience"
  },
  "tree": {
    "level": 1,
    "stage": "seed"
  }
}
```

### Step 4: 리츄얼 완료 처리
```http
PATCH /api/dashboard/rituals/123/complete
{
  "user_note": "명상 후 마음이 편안해졌어요",
  "user_mood": "calm",
  "difficulty_rating": 3
}
```
- UserStreak 업데이트 (연속 기록)
- HeartTree 성장 (+1 레벨)

## 🎯 핵심 변경사항

### app/api/v1/meari.py (수정됨)
```python
# 성장 콘텐츠 생성 API에 추가된 코드
experience_card = workflow_result.get("cards", {}).get("experience")
if experience_card:
    # DailyRitual 생성
    daily_ritual = DailyRitual(
        user_id=user_id,
        date=today,
        ritual_title=experience_card.get("ritual_name"),
        ritual_description=experience_card.get("description"),
        ritual_type="growth_experience",  # 구분자
        duration_minutes=10
    )
    db.add(daily_ritual)
```

## 📱 프론트엔드 연동

### 성장 콘텐츠 페이지
- 3종 콘텐츠 표시 (정보/경험/지원)
- experience 카드가 자동으로 대시보드에도 등록됨

### 대시보드 페이지
- "오늘의 리츄얼"로 experience 카드 표시
- 완료 버튼 클릭 → 마음나무 성장
- 캘린더에 완료 현황 표시

## ✅ 연동 완료 사항

1. ✅ 성장 콘텐츠 생성 시 DailyRitual 자동 생성
2. ✅ ritual_type으로 출처 구분 가능
3. ✅ 대시보드에서 조회 가능
4. ✅ 완료 처리 시 마음나무 성장
5. ✅ UserStreak 연속 기록 추적

## 🔍 테스트 방법

1. 서버 실행
```bash
source venv/bin/activate
python run.py
```

2. 프론트엔드 실행
```bash
cd ../meari-front
npm run dev
```

3. 플로우 테스트
- 로그인 → 태그 선택 → 성장 콘텐츠 생성
- 대시보드 확인 → "오늘의 리츄얼" 표시 확인
- 리츄얼 완료 → 마음나무 성장 확인

## 📌 주의사항

- 하루에 하나의 DailyRitual만 생성 (중복 방지)
- experience 카드만 DailyRitual로 저장
- information, support는 GeneratedCard에만 저장
- 리츄얼 완료 시 연속 기록 자동 계산