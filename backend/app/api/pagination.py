"""Pagination helpers for API responses."""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response


def add_pagination_headers(
    response: Response,
    total: int,
    limit: int,
    offset: int,
) -> Response:
    """Add pagination headers to response."""
    # Link header follows RFC 5988 (Web Linking) format
    links: dict[str, str] = {}
    
    # Calculate pages
    page = offset // limit + 1 if limit > 0 else 1
    total_pages = (total + limit - 1) // limit if total > 0 and limit > 0 else 1
    
    # Build links
    links["self"] = f"?limit={limit}&offset={offset}"
    if offset > 0:
        prev_offset = max(0, offset - limit)
        links["prev"] = f"?limit={limit}&offset={prev_offset}"
    if offset + limit < total:
        next_offset = offset + limit
        links["next"] = f"?limit={limit}&offset={next_offset}"
    
    # Build Link header value
    link_values = []
    for rel, url in links.items():
        link_values.append(f'<{url}>; rel="{rel}"')
    response.headers["Link"] = ", ".join(link_values)
    
    # Add X-Total-Count header
    response.headers["X-Total-Count"] = str(total)
    
    # Add page info
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Count"] = str(total_pages)
    response.headers["X-Limit"] = str(limit)
    
    return response


def get_pagination_params(
    request: Request,
    default_limit: int = 50,
    max_limit: int = 100,
) -> tuple[int, int]:
    """Extract pagination parameters from request query params."""
    query_params = request.query_params
    
    limit = min(
        int(query_params.get("limit", default_limit)),
        max_limit
    )
    offset = int(query_params.get("offset", 0))
    
    return limit, offset


def paginate_response(
    data: list[Any],
    total: int,
    request: Request,
    default_limit: int = 50,
    max_limit: int = 100,
) -> dict[str, Any]:
    """Create a paginated response with metadata."""
    limit, offset = get_pagination_params(request, default_limit, max_limit)
    
    total_pages = (total + limit - 1) // limit if total > 0 and limit > 0 else 1
    page = offset // limit + 1 if limit > 0 else 1
    
    return {
        "data": data,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "page": page,
            "page_count": total_pages,
            "has_previous": offset > 0,
            "has_next": offset + limit < total,
        },
    }
