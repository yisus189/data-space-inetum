#!/bin/bash
# E2E Smoke Test Script
# Run this after starting all services with docker-compose

set -e

API_URL=${API_URL:-http://localhost:8000}
KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8180}

echo "=== Data Space E2E Smoke Tests ==="
echo ""

# Helper function for colored output
green() { echo -e "\033[0;32m$1\033[0m"; }
red() { echo -e "\033[0;31m$1\033[0m"; }

# Test counter
PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local expected_status="$4"
    local data="$5"
    local auth="$6"
    
    echo -n "Testing: $name... "
    
    local curl_args="-s -o /tmp/response.txt -w %{http_code}"
    
    if [ -n "$auth" ]; then
        curl_args="$curl_args -H 'Authorization: Bearer $auth'"
    fi
    
    if [ "$method" = "POST" ]; then
        curl_args="$curl_args -X POST -H 'Content-Type: application/json'"
        if [ -n "$data" ]; then
            curl_args="$curl_args -d '$data'"
        fi
    fi
    
    local status=$(eval "curl $curl_args '$url'")
    
    if [ "$status" = "$expected_status" ]; then
        green "PASSED (HTTP $status)"
        ((PASSED++))
        return 0
    else
        red "FAILED (Expected $expected_status, got $status)"
        ((FAILED++))
        return 1
    fi
}

echo "1. Testing Health Endpoints"
echo "----------------------------"

test_endpoint "API Health" "GET" "$API_URL/health" "200"

echo ""
echo "2. Testing Public Endpoints"
echo "----------------------------"

test_endpoint "List Public Datasets" "GET" "$API_URL/datasets" "200"
test_endpoint "OpenAPI Docs" "GET" "$API_URL/docs" "200"

echo ""
echo "3. Testing Keycloak"
echo "-------------------"

test_endpoint "Keycloak Health" "GET" "$KEYCLOAK_URL/health" "200" || true
test_endpoint "Keycloak Realm" "GET" "$KEYCLOAK_URL/realms/myrealm" "200" || true

echo ""
echo "4. Testing Protected Endpoints (should return 401)"
echo "---------------------------------------------------"

test_endpoint "Protected: Create Dataset" "POST" "$API_URL/datasets" "401" '{"title":"test"}'
test_endpoint "Protected: Storage Presign" "POST" "$API_URL/storage/presign" "401" '{"filename":"test.csv"}'

echo ""
echo "=== Test Summary ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    green "All tests passed!"
    exit 0
else
    red "Some tests failed!"
    exit 1
fi
