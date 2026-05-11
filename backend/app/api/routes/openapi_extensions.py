"""OpenAPI extensions: error response schemas."""

from __future__ import annotations

# Error response schemas for OpenAPI
ERROR_RESPONSE_404 = {
    "description": "Resource not found",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail"],
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "Resource not found",
                    },
                },
            },
            "example": {"detail": "Resource not found"},
        },
    },
}

ERROR_RESPONSE_422 = {
    "description": "Validation error",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail", "errors"],
                "properties": {
                    "detail": {"type": "string", "example": "Validation error"},
                    "errors": {
                        "type": "array",
                        "items": {"type": "object"},
                        "example": [{"loc": ["body", "field"], "msg": "field required"}],
                    },
                },
            },
        },
    },
}

PaginationLinksSchema = {
    "type": "object",
    "properties": {
        "next": {"type": "string", "description": "Link to next page"},
        "prev": {"type": "string", "description": "Link to previous page"},
        "first": {"type": "string", "description": "Link to first page"},
        "last": {"type": "string", "description": "Link to last page"},
    },
}

PaginationHeadersSchema = {
    "description": "Pagination headers",
    "headers": {
        "Link": {
            "schema": PaginationLinksSchema,
            "description": "Pagination links following RFC 5988",
        },
        "X-Total-Count": {
            "schema": {"type": "integer"},
            "description": "Total number of items across all pages",
        },
        "X-Page": {
            "schema": {"type": "integer"},
            "description": "Current page number",
        },
        "X-Page-Count": {
            "schema": {"type": "integer"},
            "description": "Total number of pages",
        },
        "X-Limit": {
            "schema": {"type": "integer"},
            "description": "Maximum number of items per page",
        },
    },
}

RateLimitingHeadersSchema = {
    "description": "Rate limiting headers",
    "headers": {
        "X-RateLimit-Limit": {
            "schema": {"type": "integer"},
            "description": "Maximum number of requests allowed in the current window",
        },
        "X-RateLimit-Remaining": {
            "schema": {"type": "integer"},
            "description": "Number of requests remaining in the current window",
        },
        "X-RateLimit-Reset": {
            "schema": {"type": "integer"},
            "description": "Unix timestamp when the rate limit window resets",
        },
        "Retry-After": {
            "schema": {"type": "integer"},
            "description": "Seconds to wait before retrying after rate limit is exceeded",
        },
    },
}

RATE_LIMIT_429_RESPONSE = {
    "description": "Rate limit exceeded",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail", "retry_after"],
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "Rate limit exceeded",
                    },
                    "retry_after": {
                        "type": "integer",
                        "example": 60,
                    },
                },
            },
            "example": {
                "detail": "Rate limit exceeded",
                "retry_after": 60,
            },
        },
    },
    "headers": RateLimitingHeadersSchema,
}
