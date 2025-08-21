#!/bin/bash

echo "=== 동시 사용자 30명 테스트 ==="
echo "시작 시간: $(date +%H:%M:%S)"
echo "대상 서버: http://localhost:80"
echo ""

# 결과 저장용 변수
success_count=0
fail_count=0

# 백그라운드에서 30개 요청 동시 실행
for i in $(seq 1 30); do
  (
    tag_id=$((1 + ($i % 9)))  # 1-9 태그 순환
    start_time=$(date +%s.%N)
    
    result=$(curl -X POST "http://localhost/api/v1/meari/sessions" \
      -H "Content-Type: application/json" \
      -H "Cookie: session=test-user-$i" \
      -d "{\"selected_tag_id\": $tag_id, \"user_context\": \"사용자 $i 동시 테스트\"}" \
      -o /dev/null -s -w "%{http_code}" 2>/dev/null)
    
    end_time=$(date +%s.%N)
    elapsed=$(echo "$end_time - $start_time" | bc)
    
    if [ "$result" = "201" ] || [ "$result" = "200" ]; then
      echo "✅ 사용자 $i (태그 $tag_id): 성공 - ${elapsed}초"
    else
      echo "❌ 사용자 $i (태그 $tag_id): 실패 HTTP $result - ${elapsed}초"
    fi
  ) &
done

# 모든 백그라운드 작업 대기
wait

echo ""
echo "종료 시간: $(date +%H:%M:%S)"
echo "=== 테스트 완료 ==="

# 결과 요약
echo ""
echo "=== 결과 요약 ==="
echo "총 요청: 30"
echo "성공한 요청 수를 확인하려면 위 로그를 참조하세요"