from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Module-level limiter shared across all route files.
# Attach to app via:  app.state.limiter = limiter
# Register handler:   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Register middleware: app.add_middleware(SlowAPIMiddleware)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
