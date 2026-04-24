# Rate Limiting Headers Implementation Notes

## Required Changes

### 1. Middleware (api/middleware/ratelimit.py)
Create middleware to add X-RateLimit headers

### 2. OpenAPI Schema (docs/openapi.yaml)
Add 429 response examples for rate-limited endpoints

## Implementation Plan
1. Create rate limiting middleware class
2. Register with FastAPI app
3. Add documentation in OpenAPI schema
4. Write pytest tests

## References
- Issue #51
- FastAPI middleware docs
