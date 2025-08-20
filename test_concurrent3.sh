#!/bin/bash

echo "=== 동시 사용자 3명 테스트 ==="
echo "시작 시간: $(date +%H:%M:%S)"

# 백그라운드에서 3개 요청 동시 실행
for i in 1 2 3; do
  (
    tag_id=$((1 + ($i % 3) + 1))  # 2, 3, 4 순환
    result=$(curl -X POST "http://localhost:8001/api/v1/meari/sessions" \
      -H "Content-Type: application/json" \
      -H "Cookie: session=a84af8d0-7e46-4eae-95b5-b9a6881bcf7b" \
      -d "{\"selected_tag_id\": $tag_id, \"user_context\": \"사용자 $i 동시 테스트\"}" \
      -o /dev/null -s -w "%{http_code}:%{time_total}" 2>/dev/null)
    
    code=$(echo $result | cut -d: -f1)
    time=$(echo $result | cut -d: -f2)
    
    if [ "$code" = "201" ] || [ "$code" = "200" ]; then
      echo "✅ 사용자 $i: 성공 (${time}초)"
    else
      echo "❌ 사용자 $i: 실패 HTTP $code (${time}초)"
    fi
  ) &
done

# 모든 백그라운드 작업 대기
wait
echo "종료 시간: $(date +%H:%M:%S)"
echo "=== 테스트 완료 ==="
