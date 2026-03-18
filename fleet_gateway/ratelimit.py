"""
fleet_gateway.ratelimit — Per-backend rate limiting.

Simple sliding-window rate limiter. Backends can declare a ``rate_limit``
(requests per minute) in their config:

    backends:
      groq:
        rate_limit: 30   # free tier: 30 req/min

The router instantiates one limiter per backend and calls ``acquire()``
before each request. If the quota is exceeded the call blocks until a
slot opens, up to ``timeout`` seconds, then returns False so the router
can skip to the next backend.

Zero external dependencies — stdlib only (threading + time).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """Sliding-window rate limiter (thread-safe).

    Args:
        requests_per_minute: Maximum requests allowed per 60-second window.
            Use 0 or None to disable limiting.
    """

    def __init__(self, requests_per_minute: Optional[int]):
        self._rpm = requests_per_minute or 0
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._rpm > 0

    def acquire(self, timeout: float = 30.0) -> bool:
        """Block until a request slot is available.

        Returns:
            True if a slot was acquired.
            False if ``timeout`` was exceeded before a slot opened.
        """
        if not self.enabled:
            return True

        window = 60.0
        deadline = time.monotonic() + timeout

        while True:
            with self._lock:
                now = time.monotonic()
                # Expire timestamps outside the window
                while self._timestamps and now - self._timestamps[0] >= window:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._rpm:
                    self._timestamps.append(now)
                    return True

                # Compute how long until the oldest slot expires
                wait = window - (now - self._timestamps[0]) + 0.01

            remaining = deadline - time.monotonic()
            if wait > remaining:
                return False  # Would exceed timeout
            time.sleep(min(wait, 1.0))

    def __repr__(self) -> str:
        if not self.enabled:
            return "RateLimiter(disabled)"
        return f"RateLimiter({self._rpm} rpm)"
