import time
from collections import defaultdict, deque

from .config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        if not settings.rate_limit_enabled:
            return True
        now = time.time()
        window_start = now - 60
        events = self._events[key]
        while events and events[0] < window_start:
            events.popleft()
        if len(events) >= settings.rate_limit_per_minute:
            return False
        events.append(now)
        return True


rate_limiter = RateLimiter()

