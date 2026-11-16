import math
import time
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Decision:
    allowed: bool
    remaining: int
    retry_after: int  # seconds until the client may try again (0 if allowed)


class RateLimiter(Protocol):
    async def check(self, key: str) -> Decision: ...


class FixedWindowMemoryLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clients: dict[str, dict] = {}

    async def check(self, key: str) -> Decision:
        now = time.time()
        client_data = self.clients.get(key)

        # New client, or its window has expired: start a fresh window.
        if client_data is None or now - client_data["window_start"] >= self.window_seconds:
            self.clients[key] = {"count": 1, "window_start": now}
            return Decision(allowed=True, remaining=self.limit - 1, retry_after=0)

        if client_data["count"] >= self.limit:
            window_end = client_data["window_start"] + self.window_seconds
            return Decision(
                allowed=False,
                remaining=0,
                retry_after=math.ceil(window_end - now),
            )

        client_data["count"] += 1
        return Decision(
            allowed=True,
            remaining=self.limit - client_data["count"],
            retry_after=0,
        )
