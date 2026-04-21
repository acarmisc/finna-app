#!/bin/bash
# Fast E2E Test Runner for FinOps Backend API
# Tests backend API endpoints without UI

set -e

echo "========================================"
echo "FinOps Backend E2E Tests"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
ISSUES=()
API_BASE="http://localhost:8000"

# Wait for API to be ready (max 30s)
echo -n "Waiting for API... "
for i in {1..30}; do
    if curl -s "${API_BASE}/healthz" | grep -q '"status":"ok"'; then
        echo -e "${GREEN}READY${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}TIMEOUT${NC}"
        echo "API not responding after 30s"
        exit 1
    fi
done

# Authenticate first
echo -n "Test 1: Auth token endpoint... "
TOKEN_RESPONSE=$(curl -s --max-time 10 "${API_BASE}/api/v1/auth/token" \
    -X POST -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin"}')
if echo "$TOKEN_RESPONSE" | grep -q '"token"'; then
    echo -e "${GREEN}PASSED${NC}"
    TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("token",""))')
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Auth token endpoint not working")
    ((FAILED++))
fi

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

# Test 2: Costs endpoint
echo -n "Test 2: Costs API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/costs" -H "$AUTH_HEADER" | grep -q '"costs"'; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Costs endpoint returning errors")
    ((FAILED++))
fi

# Test 3: Alerts endpoint
echo -n "Test 3: Alerts API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/alerts" -H "$AUTH_HEADER" | grep -q '"alerts"'; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Alerts endpoint returning errors")
    ((FAILED++))
fi

# Test 4: Config endpoint
echo -n "Test 4: Config API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/config" -H "$AUTH_HEADER" | grep -q '\['; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Config endpoint returning errors")
    ((FAILED++))
fi

# Test 5: Projects endpoint
echo -n "Test 5: Projects API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/config/projects" -H "$AUTH_HEADER" | grep -q 'id'; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Projects endpoint returning errors")
    ((FAILED++))
fi

# Test 6: Costs daily endpoint
echo -n "Test 6: Costs daily API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/costs/daily" -H "$AUTH_HEADER" | grep -q 'date'; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Costs daily endpoint returning errors")
    ((FAILED++))
fi

# Test 7: Extractors endpoint
echo -n "Test 7: Extractors API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/extractors/status" -H "$AUTH_HEADER" | grep -q 'runs'; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Extractors endpoint returning errors")
    ((FAILED++))
fi

# Test 8: Costs by SKU
echo -n "Test 8: Costs by SKU API... "
if curl -s --max-time 10 "${API_BASE}/api/v1/costs/by-sku" -H "$AUTH_HEADER" | grep -q 'sku'; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}FAILED${NC}"
    ISSUES+=("Costs by SKU endpoint returning errors")
    ((FAILED++))
fi

# Test 9: API docs
echo -n "Test 9: API docs... "
if curl -s --max-time 10 "${API_BASE}/docs" | grep -q "FinOps"; then
    echo -e "${GREEN}PASSED${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${YELLOW}PENDING${NC}"
    ISSUES+=("API documentation not loading")
    ((FAILED++))
fi

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ ${#ISSUES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Issues found:${NC}"
    for i in "${!ISSUES[@]}"; do
        issue_num=$((i + 1))
        echo "  Issue #$issue_num: ${ISSUES[$i]}"
    done
fi

if [ $FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}E2E tests completed with $FAILED failures${NC}"
    exit 1
else
    echo -e "${GREEN}All E2E tests passed!${NC}"
    exit 0
fi
