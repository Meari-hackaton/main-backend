#!/bin/bash

echo "=== 동시 사용자 2명 테스트 ==="

# 백그라운드에서 2개 요청 동시 실행
for i in 1 2; do
  (
    echo "사용자 $i 시작: $(date +%H:%M:%S)"
    time curl -X POST "http://localhost:8001/api/v1/meari/sessions" \
      -H "Content-Type: application/json" \
      -H "Cookie: session=a84af8d0-7e46-4eae-95b5-b9a6881bcf7b" \
      -d "{\"selected_tag_id\": $((1 + $i)), \"user_context\": \"사용자 $i 테스트\"}" \
      -o /dev/null -s -w "사용자 $i: HTTP %{http_code} - %{time_total}초\n"
  ) &
done

# 모든 백그라운드 작업 대기
wait
echo "=== 테스트 완료 ==="
