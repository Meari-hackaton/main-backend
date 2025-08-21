# 메아리 LangGraph 워크플로우 플로우 다이어그램

## 1. 초기 세션 (Initial Session) - `/api/meari-sessions`
```
[시작] 
   ↓
[Supervisor] → routing_type = "initial_session"
   ↓
[병렬 실행]
   ├─[EmpathyAgent] → 공감 카드 3개 생성 (Vector RAG)
   └─[CypherAgent] → Graph RAG (Neo4j 쿼리)
   ↓
[병합] → graph_results 전달
   ↓
[ReflectionAgent] → 성찰 카드 3개 생성 (graph_results 기반)
   ↓
[PersonaAgent] → 초기 페르소나 생성 (공감+성찰 카드 기반)
   ↓
[CardSynthesizer] → 최종 응답 구조화
   ↓
[종료] → 공감 카드 + 성찰 카드 + 페르소나 반환
```

### 초기 세션 결과:
- **공감의 메아리**: 3개 카드 (사용자 감정 공감)
- **성찰의 메아리**: 3개 카드 (사회적 맥락 분석)
- **초기 페르소나**: 사용자 이해 요약
- **LLM 호출**: 4회 (Cypher, Empathy, Reflection, Persona)

---

## 2. 성장 콘텐츠 (Growth Content) - `/api/growth-contents`
```
[시작]
   ↓
[Supervisor] → routing_type = "growth_content"
   ↓
[GrowthAgent] → 3종 콘텐츠 생성
   ├─ 정보 (information): WebSearch 준비
   ├─ 경험 (experience): 리츄얼 제안
   └─ 지원 (support): 정책 검색 (Milvus)
   ↓
[CardSynthesizer] → 최종 응답 구조화
   ↓
[종료] → 성장의 메아리 3종 반환
```

### 성장 콘텐츠 결과:
- **성장의 메아리**: 
  - 정보 카드: 유용한 정보
  - 경험 카드: 10분 리츄얼
  - 지원 카드: 맞춤 정책
- **LLM 호출**: 1회 (정보+경험 통합 생성)

---

## 3. 리츄얼 (Ritual) - `/api/rituals`
```
[시작]
   ↓
[Supervisor] → routing_type = "ritual"
   ↓
[PersonaAgent] → 페르소나 업데이트
   ↓
[CardSynthesizer] → 리츄얼 응답 구조화
   ↓
[종료] → 페르소나 업데이트 + 마음나무 상태
```

### 리츄얼 결과:
- **페르소나 업데이트**: 깊이 증가
- **마음나무 상태**: 성장 단계 반환
- **LLM 호출**: 1회 (페르소나 업데이트)

---

## 핵심 분리 포인트

### 1. **초기 세션과 성장 콘텐츠는 완전히 분리**
- 초기 세션: 공감 + 성찰 + 페르소나만
- 성장 콘텐츠: 별도 API 호출 필요
- 각각 독립적인 LangGraph 상태로 실행

### 2. **API 엔드포인트별 역할**
- `/api/meari-sessions`: 최초 1회만 (공감+성찰)
- `/api/growth-contents`: 매일 호출 가능 (성장 콘텐츠)
- `/api/rituals`: 리츄얼 기록 시 (페르소나 업데이트)

### 3. **상태 관리**
- 각 요청은 독립적인 LangGraph 인스턴스
- 상태는 요청 단위로 생성되고 종료
- DB에 저장된 데이터만 유지

### 4. **LLM 호출 최적화**
- 초기 세션: 4회 (병렬 처리로 시간 단축)
- 성장 콘텐츠: 1회
- 리츄얼: 1회