import html
import time
from typing import Dict, List, Optional
from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

def sanitize_string(val: Optional[str]) -> Optional[str]:
    """
    Escapes HTML markup entities inside string inputs to neutralize cross-site scripting (XSS).
    If input is None, returns early to preserve model schema options.
    """
    if val is None:
        return None
    # strip leading/trailing spaces and escape HTML special characters (<, >, &, etc.)
    return html.escape(val.strip())

class RateLimiter:
    """
    A sliding-window rate limiter keeping request counts in-memory.
    Designed to protect endpoints from automated scraping or brute force resource exhaustion.
    In distributed environments, this would write to a central cache like Redis.
    """
    def __init__(self, requests_limit: int, window_seconds: int):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        # maps client IP address to list of epoch timestamps
        self.history: Dict[str, List[float]] = {}

    def __call__(self, request: Request) -> None:
        # identify client by IP; fallback to localhost if headers are missing
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

        if client_ip not in self.history:
            self.history[client_ip] = []

        # evict old timestamps falling outside the sliding rate window
        self.history[client_ip] = [
            t for t in self.history[client_ip] 
            if now - t < self.window_seconds
        ]

        # guard clause checking if request limit was reached
        if len(self.history[client_ip]) >= self.requests_limit:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Request rate limit exceeded. Please wait and try again."
            )

        self.history[client_ip].append(now)

# rate limit objects configured as FastAPI route dependencies:
# 30 modifications (POST, PUT, DELETE) allowed per client per minute
write_rate_limiter = RateLimiter(requests_limit=30, window_seconds=60)
# 100 queries (GET) allowed per client per minute
read_rate_limiter = RateLimiter(requests_limit=100, window_seconds=60)
