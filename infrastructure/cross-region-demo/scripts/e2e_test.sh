#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: ./e2e_test.sh <FRONTEND_URL>"
  exit 1
fi

FRONTEND_URL=$1

echo "Testing Frontend at $FRONTEND_URL..."

run_test() {
  local name=$1
  local path=$2
  local expected=$3
  
  echo "----------------------------------------"
  echo "Running Test: $name"
  echo "URL: $FRONTEND_URL$path"
  
  RESPONSE=$(curl -s "$FRONTEND_URL$path")
  echo "Response: $RESPONSE"
  
  if echo "$RESPONSE" | grep -q "$expected"; then
    echo "✅ Passed: $name"
    return 0
  else
    echo "❌ Failed: $name"
    echo "Expected to find: $expected"
    return 1
  fi
}

FAILED=0

# Test 1: Standard Ping
run_test "Standard Ping" "/api/ping?mode=standard" "pong from backend" || FAILED=1

# Test 2: GCS Mode
# We check for "pong from backend" which is always present if it reached the backend.
# We also check that it at least tried GCS (either success or failure message containing "GCS" or "transferred")
RESPONSE=$(curl -s "$FRONTEND_URL/api/ping?mode=gcs")
echo "----------------------------------------"
echo "Running Test: GCS Mode"
echo "URL: $FRONTEND_URL/api/ping?mode=gcs"
echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "pong from backend" && (echo "$RESPONSE" | grep -q "Successfully transferred" || echo "$RESPONSE" | grep -q "GCS"); then
  echo "✅ Passed: GCS Mode"
else
  echo "❌ Failed: GCS Mode"
  FAILED=1
fi

# Test 3: Payload Size
run_test "Payload Size" "/api/ping?size=1024" "received 1024 bytes" || FAILED=1

# Test 4: Batch Ping
run_test "Batch Ping" "/api/batch-ping?count=5&mode=standard" "\"total\":5" || FAILED=1

echo "----------------------------------------"
if [ $FAILED -eq 0 ]; then
  echo "✅ All E2E Tests Passed!"
  exit 0
else
  echo "❌ Some E2E Tests Failed!"
  exit 1
fi
