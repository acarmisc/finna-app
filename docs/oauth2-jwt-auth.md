# OAuth2/JWT Authentication Implementation

## Overview

This document describes the OAuth2/JWT authentication implementation for the FinOps Orchestrator API.

## Features

- ✅ JWT token generation
- ✅ Token verification middleware
- ✅ Protected API endpoints with auth dependencies
- ✅ OAuth2 password flow for authentication
- ✅ HTTP 401 responses for invalid/missing tokens

## Dependencies

The following dependencies were already present in `pyproject.toml`:

- `python-jose[cryptography]`: JWT token encoding/decoding
- `passlib[bcrypt]`: Password hashing and verification

## Implementation Details

### API Structure

The authentication system uses the following components:

#### 1. `api/auth.py` - Core Authentication Module

Contains the core authentication functions:

**Functions:**
- `create_access_token(data, expires_delta)`: Create a JWT access token
- `verify_token(token)`: Decode and validate a JWT token
- `get_current_user(token)`: Get the current authenticated user from a token
- `require_auth(user)`: Dependency to require authentication
- `get_password_hash(password)`: Hash a password using bcrypt
- `verify_password(plain_password, hashed_password)`: Verify password against hash
- `token_verification_middleware(request, call_next)`: Middleware for auto-protection

**Constants:**
- `JWT_SECRET`: Secret key for JWT signing (from `JWT_SECRET` env var)
- `JWT_ALGORITHM`: Algorithm for JWT (default: HS256)
- `JWT_EXPIRATION_MINUTES`: Token expiration time (default: 60 minutes)

**OAuth2PasswordBearer:**
- `oauth2_scheme`: OAuth2 scheme configured at `/api/v1/auth/token`

#### 2. `api/routes/auth.py` - Authentication Endpoints

**Endpoints:**
- `POST /api/v1/auth/token`: OAuth2 password flow - exchanges credentials for JWT token
- `POST /api/v1/auth/azure/device-code`: Start Azure device code flow
- `POST /api/v1/auth/azure/device-code/poll`: Poll for Azure device code completion
- `POST /api/v1/auth/gcp/register`: Register GCP credentials

#### 3. `api/models.py` - Request/Response Schemas

Added schemas:
- `TokenRequest`: Username and password for token endpoint
- `TokenResponse`: Access token and token type

#### 4. `api/main.py` - Application Setup

Added middleware:
- `TokenVerificationMiddleware`: Auto-verify JWT on all protected routes

Protected endpoints automatically:
- Check for `Authorization: Bearer <token>` header
- Validate token signature and expiration
- Return HTTP 401 for invalid/missing tokens
- Allow `/api/v1/auth/token` and `/api/v1/healthz` without auth

### Route Protection

Protected routes now require authentication via:

1. **Manual dependency injection** in route definitions:
   ```python
   @router.get("/config", dependencies=[Depends(require_auth)])
   ```

2. **Mounted routers** with auth dependencies:
   - `/api/v1/config` - All config CRUD operations
   - `/api/v1/extractors` - All extractor operations

## Usage

### 1. Obtain a Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Use Token in Requests

```bash
curl -X GET http://localhost:8000/api/v1/config \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Token Validation

The system automatically validates:
- Token signature (using JWT_SECRET)
- Token expiration (JWT_EXPIRATION_MINUTES)
- User existence in token (sub claim)

Invalid tokens receive HTTP 401:
```json
{
  "detail": "Could not validate credentials",
  "WWW-Authenticate": "Bearer"
}
```

## Testing

Run authentication tests:

```bash
pytest tests/test_api_auth.py -v
```

Tests cover:
- Token creation with default expiry
- Token creation with custom expiry
- Token decoding/validation
- Invalid token handling (401)
- Expired token handling (401)
- Require auth dependency

## Security

### Password Storage
- Passwords are hashed using bcrypt
- Storing hashed passwords in keyring service `finna-app-api`

### Token Security
- JWT tokens expired automatically after configured time
- Tokens signed with HMAC-SHA256 (or configured algorithm)
- Middleware ensures all routes are protected unless explicitly excluded

### Environment Variables

Required:
- `JWT_SECRET`: Secret key for JWT signing (min 32 chars recommended)
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_EXPIRATION_MINUTES`: Token validity time (default: 60)

## Future Enhancements

- [ ] Add refresh token support
- [ ] Implement token revocation
- [ ] Add rate limiting per user
- [ ] Support for OAuth2 implicit flow
- [ ] Add token introspection endpoint
- [ ] Implement multi-factor authentication

## Troubleshooting

### Common Issues

1. **401 "Could not validate credentials"**
   - Check JWT_SECRET is set
   - Check token hasn't expired
   - Verify token format is correct

2. **Middleware not working**
   - Ensure middleware is registered before routers
   - Check token endpoint is not protected
   - Verify healthz endpoint is not protected

3. **Token endpoint returns error**
   - Check password is hashed correctly
   - Verify keyring service name
   - Check username exists in keyring

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [OAuth2 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
