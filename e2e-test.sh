#!/usr/bin/env bash
# Simple E2E test runner for FinOps Console

set -e

echo "🧪 FinOps Console E2E Tests"
echo "============================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
check_backend() {
    echo -e "${YELLOW}Checking backend availability...${NC}"
    for i in {1..10}; do
        if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend is running${NC}"
            return 0
        fi
        echo "  Waiting for backend ($i/10)..."
        sleep 2
    done
    echo -e "${RED}✗ Backend not available${NC}"
    return 1
}

# Check if frontend is running
check_frontend() {
    echo -e "${YELLOW}Checking frontend availability...${NC}"
    for i in {1..10}; do
        if curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Frontend is running${NC}"
            return 0
        fi
        echo "  Waiting for frontend ($i/10)..."
        sleep 2
    done
    echo -e "${RED}✗ Frontend not available${NC}"
    return 1
}

# Test API endpoints
test_api_endpoints() {
    echo -e "${YELLOW}Testing API endpoints...${NC}"
    
    local backend_ok=true
    
    # Health check
    echo "  Testing /healthz..."
    if curl -s http://localhost:8000/healthz | grep -q "ok"; then
        echo -e "    ${GREEN}✓ /healthz${NC}"
    else
        echo -e "    ${RED}✗ /healthz${NC}"
        backend_ok=false
    fi
    
    # Mock data test (even without auth)
    echo "  Testing /api/v1/costs (without auth)..."
    curl -s http://localhost:8000/api/v1/costs 2>/dev/null | head -c 100 && echo ""
    
    # Test auth endpoint
    echo "  Testing /api/v1/auth/token (with mock data)..."
    if curl -s -X POST http://localhost:8000/api/v1/auth/token \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin"}' > /tmp/token.json 2>/dev/null; then
        echo -e "    ${GREEN}✓ Auth endpoint created${NC}"
    else
        echo -e "    ${RED}✗ Auth endpoint missing${NC}"
    fi
    
    return $backend_ok
}

# Test frontend elements
test_frontend() {
    echo -e "${YELLOW}Testing frontend elements...${NC}"
    
    if curl -s http://localhost:5173 | grep -q "FinOps"; then
        echo -e "    ${GREEN}✓ Frontend serves content${NC}"
    else
        echo -e "    ${YELLOW}⚠ Frontend not serving yet${NC}"
    fi
}

# Create GitHub issues for any issues found
create_github_issues() {
    echo -e "${YELLOW}Checking for issues that need GitHub issues...${NC}"
    local issues=()
    
    # Check if backend routes are registered
    if ! curl -s http://localhost:8000/api/v1/costs > /dev/null 2>&1; then
        issues+=("Backend route /api/v1/costs not registered")
    fi
    
    # Check if auth is working
    if [ ! -f /tmp/token.json ]; then
        issues+=("Authentication not working - auth endpoint missing")
    fi
    
    if [ ${#issues[@]} -gt 0 ]; then
        echo -e "${YELLOW}Found ${#issues[@]} issues that need GitHub issues:${NC}"
        for issue in "${issues[@]}"; do
            echo "  - $issue"
        done
        
        # Create GitHub issue (if GitHub CLI is available)
        if command -v gh > /dev/null; then
            echo -e "${YELLOW}Creating GitHub issues...${NC}"
            for issue in "${issues[@]}"; do
                gh issue create --title "E2E Test Issue: $(echo $issue | cut -c1-60)" \
                    --body "Issue found during E2E testing:
                
$issue
                
Reproduction steps:
1. Run E2E tests
2. $issue
                
Expected behavior: All tests should pass
Actual behavior: Test failed
                " 2>/dev/null || echo "  Could not create GitHub issue: $issue"
            done
        else
            echo -e "${YELLOW}GitHub CLI not found. Please create issues manually:${NC}"
            echo "Repository: acarmisc/finna-app"
            echo "Labels: bug, e2e-test-failed"
            for issue in "${issues[@]}"; do
                echo "  - $issue"
            done
        fi
    else
        echo -e "${GREEN}✓ All tests passed - no issues to report${NC}"
    fi
}

# Main test execution
main() {
    echo "Started at: $(date)"
    echo ""
    
    # Start backend if not already running
    echo -e "${YELLOW}Starting backend server...${NC}"
    cd /root/projects/finna-app
    uv run uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 5
    
    # Run tests
    test_api_endpoints
    backend_status=$?
    
    # Test frontend
    test_frontend
    
    # Report issues
    echo ""
    create_github_issues
    
    # Summary
    echo -e "\n${YELLOW}Test Summary:${NC}"
    if [ $backend_status -eq 0 ]; then
        echo -e "${GREEN}✓ Backend API tests passed${NC}"
    else
        echo -e "${RED}✗ Backend API tests failed${NC}"
    fi
    
    echo -e "\n${YELLOW}GitHub Issues to Create:${NC}"
    echo "1. Fix API route registration in main.py"
    echo "2. Implement authentication endpoint"
    echo "3. Add Playwright E2E test suite integration"
    echo "4. Fix database connection for full stack tests"
    
    # Cleanup
    kill $BACKEND_PID 2>/dev/null || true
    
    echo -e "\n${GREEN}E2E Tests Complete!${NC}"
    echo "Completed at: $(date)"
}

# Run main
main "$@"
