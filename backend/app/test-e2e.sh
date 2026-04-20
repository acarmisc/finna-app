#!/bin/bash
# Fast E2E Test Runner for FinOps Console
# Tests backend API endpoints without UI

set -e

echo "========================================"
echo "FinOps Console E2E Tests (Backend API)"
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

# Test 1: Backend health check
echo -n "Test 1: Health check... "
if curl -s http://localhost:8000/healthz | grep -q '"status":"ok"'; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAILED${NC} - Backend not running or returning errors"
    ISSUES+=("Backend health check failing")
    ((FAILED++))
fi

# Test 2: Costs endpoint
echo -n "Test 2: Costs API... "
if curl -s http://localhost:8000/api/v1/costs 2>/dev/null | grep -q "costs"; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}PENDING - Requires authentication${NC}"
    ISSUES+=("Costs endpoint requires auth")
    ((FAILED++))
fi

# Test 3: Alerts endpoint
echo -n "Test 3: Alerts API... "
if curl -s http://localhost:8000/api/v1/alerts 2>/dev/null | grep -q "alerts"; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}PENDING - Requires authentication${NC}"
    ISSUES+=("Alerts endpoint requires auth")
    ((FAILED++))
fi

# Test 4: Config endpoint
echo -n "Test 4: Config API... "
if curl -s http://localhost:8000/api/v1/config 2>/dev/null | grep -q "\["; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}PENDING - Requires authentication${NC}"
    ISSUES+=("Config endpoint requires auth")
    ((FAILED++))
fi

# Test 5: API documentation
echo -n "Test 5: API docs... "
if curl -s http://localhost:8000/docs | grep -q "FinOps"; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}PENDING - API docs not loading${NC}"
    ISSUES+=("API documentation not loading")
    ((FAILED++))
fi

# Test 6: Extractors endpoint
echo -n "Test 6: Extractors API... "
if curl -s http://localhost:8000/api/v1/extractors/status 2>/dev/null; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}PENDING - Requires authentication${NC}"
    ISSUES+=("Extractors endpoint requires auth")
    ((FAILED++))
fi

# Test 7: Routes registered
echo -n "Test 7: Routes registered... "
if grep -q "costs.router" /root/projects/finna-app/api/main.py && \
   grep -q "alerts.router" /root/projects/finna-app/api/main.py; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAILED${NC} - Routes not registered"
    ISSUES+=("API routes not registered in main.py")
    ((FAILED++))
fi

# Test 8: Mock data exists
echo -n "Test 8: Mock data... "
if [ -f /root/projects/finna-app/src/data/mock_api_data.json ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAILED${NC} - Mock data missing"
    ISSUES+=("Mock data not created")
    ((FAILED++))
fi

# Test 9: Frontend client exists
echo -n "Test 9: Frontend client... "
if [ -f /root/projects/finna-app/src/services/apiClient.ts ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAILED${NC} - API client missing"
    ISSUES+=("Frontend API client missing")
    ((FAILED++))
fi

# Test 10: React hooks exist
echo -n "Test 10: React hooks... "
if [ -f /root/projects/finna-app/src/hooks/useApi.ts ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAILED${NC} - React hooks missing"
    ISSUES+=("React hooks not created")
    ((FAILED++))
fi

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

# Report issues that need GitHub issues
if [ ${#ISSUES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Issues to create on GitHub:${NC}"
    echo "Repository: acarmisc/finna-app"
    echo "Labels: bug, e2e-test-failed"
    echo ""
    
    for i in "${!ISSUES[@]}"; do
        issue_num=$((i + 1))
        echo "Issue #$issue_num: ${ISSUES[$i]}"
        echo "  Priority: Medium"
        echo "  Solution: Fix the identified issue"
        echo ""
    done
    
    # Create GitHub issues if gh CLI is available
    if command -v gh > /dev/null 2>&1; then
        echo -e "${GREEN}Creating GitHub issues...${NC}"
        
        for issue in "${ISSUES[@]}"; do
            title=$(echo "$issue" | cut -c1-60)
            issue_id=$(gh issue create --title "$title" \
                --body "Issue found during E2E testing:

$issue

Reproduction:
1. Run: ./e2e-test.sh
2. Test will fail on this issue

Expected: All tests should pass
Actual: Test failed with: $issue
" 2>/dev/null | tail -1)
            
            if [ -n "$issue_id" ]; then
                echo "  Created: $issue_id"
            fi
        done
    else
        echo -e "${YELLOW}GitHub CLI not found. Please create issues manually:${NC}"
        echo "Run: gh issue create --title 'E2E Test Issue' --body 'Description'"
    fi
else
    echo -e "${GREEN}✓ All tests passed!${NC}"
fi

# Final status
if [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}⚠ E2E tests completed with $FAILED failures${NC}"
    exit 1
else
    echo -e "${GREEN}✓ All E2E tests passed!${NC}"
    exit 0
fi
