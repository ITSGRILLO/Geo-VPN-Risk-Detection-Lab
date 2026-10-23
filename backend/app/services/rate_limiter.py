"""
services/rate_limiter.py

In-memory sliding-window rate limiter, keyed by IP. Deliberately not
persisted to a DB for the MVP — the goal here is proving the scoring
pipeline works, not building durable state. Swappable for Redis later
without touching route code, since it's exposed as a class with a
narrow interface.
"""

import time
from collections import defaultdict, deque
from threading import Lock

WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 10


class RateLimiter:
    """
    Tracks request timestamps per IP in a sliding 60-second window.

    Thread-safety: a single Lock guards all state. Fine for a local
    single-process MVP; if this ever runs behind multiple workers,
    swap the internals for Redis (INCR + EXPIRE or a sorted set) and
    keep the same public methods so callers don't change.
    """

    def __init__(self, window_seconds: int = WINDOW_SECONDS, max_requests: int = MAX_REQUESTS_PER_WINDOW):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._blocked_until: dict[str, float] = {}
        self._lock = Lock()

    def _prune_old(self, ip: str, now: float) -> None:
        """Drop timestamps outside the current window for this IP."""
        window = self._requests[ip]
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently under a temporary block."""
        now = time.time()
        blocked_until = self._blocked_until.get(ip)
        if blocked_until is None:
            return False
        if now >= blocked_until:
            # Block expired — clean up so future checks are O(1) again.
            del self._blocked_until[ip]
            return False
        return True

    def record_request(self, ip: str) -> int:
        """
        Record a request for this IP and return the current count
        within the sliding window. Does NOT block by itself — call
        `check_and_block` for the enforce-then-429 behavior.
        """
        with self._lock:
            now = time.time()
            self._prune_old(ip, now)
            self._requests[ip].append(now)
            return len(self._requests[ip])

    def check_and_block(self, ip: str) -> tuple[int, bool]:
        """
        Record a request, then block the IP if it exceeded the limit.

        Returns:
            (requests_in_window, newly_blocked) — newly_blocked is True
            only on the request that triggers the block, so callers can
            distinguish "already blocked" from "just tipped over".
        """
        with self._lock:
            now = time.time()
            self._prune_old(ip, now)
            self._requests[ip].append(now)
            count = len(self._requests[ip])

            if count > self.max_requests and ip not in self._blocked_until:
                self._blocked_until[ip] = now + self.window_seconds
                return count, True

            return count, False

    def requests_in_window(self, ip: str) -> int:
        """Read-only count of requests in the current window, no side effects."""
        now = time.time()
        self._prune_old(ip, now)
        return len(self._requests[ip])


# Single shared instance for the app — imported by the /analyze route.
rate_limiter = RateLimiter()