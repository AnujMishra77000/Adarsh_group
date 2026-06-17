from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic

import redis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LoginLimitStatus:
    allowed: bool
    retry_after_seconds: int = 0


class LoginRateLimiter:
    def __init__(self) -> None:
        self._redis_client: redis.Redis | None = None
        self._redis_unavailable = False
        self._attempts_by_key: dict[str, deque[float]] = defaultdict(deque)
        self._failed_attempts_by_key: dict[str, tuple[int, float]] = {}
        self._lockout_until_by_key: dict[str, float] = {}

    @staticmethod
    def build_key(ip_address: str | None, shop_key: str, login_identifier: str) -> str:
        raw_key = "|".join(
            [
                (ip_address or "unknown").strip().lower(),
                shop_key.strip().lower(),
                login_identifier.strip().lower(),
            ]
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def check_rate_limit(self, key: str) -> LoginLimitStatus:
        if redis_client := self._get_redis_client():
            return self._check_redis_rate_limit(redis_client, key)
        return self._check_memory_rate_limit(key)

    def check_lockout(self, key: str) -> LoginLimitStatus:
        if redis_client := self._get_redis_client():
            return self._check_redis_lockout(redis_client, key)
        return self._check_memory_lockout(key)

    def record_failed_attempt(self, key: str) -> LoginLimitStatus:
        if redis_client := self._get_redis_client():
            return self._record_redis_failed_attempt(redis_client, key)
        return self._record_memory_failed_attempt(key)

    def record_success(self, key: str) -> None:
        if redis_client := self._get_redis_client():
            redis_client.delete(self._failed_key(key), self._lockout_key(key))
            return

        self._failed_attempts_by_key.pop(key, None)
        self._lockout_until_by_key.pop(key, None)

    def reset(self) -> None:
        self._attempts_by_key.clear()
        self._failed_attempts_by_key.clear()
        self._lockout_until_by_key.clear()

    def _get_redis_client(self) -> redis.Redis | None:
        if self._redis_unavailable:
            return None
        if self._redis_client is not None:
            return self._redis_client

        try:
            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            self._redis_client = client
            return client
        except Exception as exc:
            self._redis_unavailable = True
            logger.warning("auth.rate_limiter.redis_unavailable", error=str(exc))
            return None

    @staticmethod
    def _attempts_key(key: str) -> str:
        return f"auth:login:attempts:{key}"

    @staticmethod
    def _failed_key(key: str) -> str:
        return f"auth:login:failed:{key}"

    @staticmethod
    def _lockout_key(key: str) -> str:
        return f"auth:login:lockout:{key}"

    def _check_redis_rate_limit(self, redis_client: redis.Redis, key: str) -> LoginLimitStatus:
        attempts_key = self._attempts_key(key)
        attempts = int(redis_client.incr(attempts_key))
        if attempts == 1:
            redis_client.expire(attempts_key, settings.auth_login_rate_limit_window_seconds)
        if attempts > settings.auth_login_rate_limit_attempts:
            ttl = max(redis_client.ttl(attempts_key), 1)
            return LoginLimitStatus(allowed=False, retry_after_seconds=ttl)
        return LoginLimitStatus(allowed=True)

    def _check_redis_lockout(self, redis_client: redis.Redis, key: str) -> LoginLimitStatus:
        lockout_key = self._lockout_key(key)
        if not redis_client.exists(lockout_key):
            return LoginLimitStatus(allowed=True)
        ttl = max(redis_client.ttl(lockout_key), 1)
        return LoginLimitStatus(allowed=False, retry_after_seconds=ttl)

    def _record_redis_failed_attempt(self, redis_client: redis.Redis, key: str) -> LoginLimitStatus:
        failed_key = self._failed_key(key)
        attempts = int(redis_client.incr(failed_key))
        redis_client.expire(failed_key, settings.auth_login_lockout_seconds)
        if attempts < settings.auth_login_lockout_failed_attempts:
            return LoginLimitStatus(allowed=True)

        redis_client.setex(self._lockout_key(key), settings.auth_login_lockout_seconds, "1")
        return LoginLimitStatus(allowed=False, retry_after_seconds=settings.auth_login_lockout_seconds)

    def _check_memory_rate_limit(self, key: str) -> LoginLimitStatus:
        now = monotonic()
        cutoff = now - settings.auth_login_rate_limit_window_seconds
        attempts = self._attempts_by_key[key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        attempts.append(now)

        if len(attempts) > settings.auth_login_rate_limit_attempts:
            oldest = attempts[0]
            retry_after = int(max(settings.auth_login_rate_limit_window_seconds - (now - oldest), 1))
            return LoginLimitStatus(allowed=False, retry_after_seconds=retry_after)
        return LoginLimitStatus(allowed=True)

    def _check_memory_lockout(self, key: str) -> LoginLimitStatus:
        now = monotonic()
        lockout_until = self._lockout_until_by_key.get(key)
        if lockout_until is None or lockout_until <= now:
            self._lockout_until_by_key.pop(key, None)
            return LoginLimitStatus(allowed=True)
        return LoginLimitStatus(allowed=False, retry_after_seconds=int(max(lockout_until - now, 1)))

    def _record_memory_failed_attempt(self, key: str) -> LoginLimitStatus:
        now = monotonic()
        count, first_attempt_at = self._failed_attempts_by_key.get(key, (0, now))
        if now - first_attempt_at > settings.auth_login_lockout_seconds:
            count = 0
            first_attempt_at = now

        count += 1
        self._failed_attempts_by_key[key] = (count, first_attempt_at)
        if count < settings.auth_login_lockout_failed_attempts:
            return LoginLimitStatus(allowed=True)

        lockout_until = now + settings.auth_login_lockout_seconds
        self._lockout_until_by_key[key] = lockout_until
        return LoginLimitStatus(allowed=False, retry_after_seconds=settings.auth_login_lockout_seconds)


login_rate_limiter = LoginRateLimiter()
