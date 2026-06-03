"""Shared slowapi limiter for the API.

Imported by `main.py` (to attach to app.state and register the handler) and by
route modules (to apply `@limiter.limit(...)` decorators). Keeping a single
module-level instance avoids the circular-import gymnastics of putting the
limiter directly in main.py.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global default — applied to every request that does not opt out.
# Overridable via env for ops tuning without code changes.
_DEFAULT_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[_DEFAULT_LIMIT])

# Tighter floors for auth-style endpoints (login, OAuth, password reset).
AUTH_LIMIT = os.getenv("RATE_LIMIT_AUTH", "5/minute")
