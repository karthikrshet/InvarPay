"""
InvarPay AI — Phase 7: Rate Limiting Middleware

Per-tenant, per-endpoint rate limiting using Redis.
Sliding window algorithm for accurate throttling.

Limits (configurable):
- Webhook ingestion: 1000/min per org
- Payment initiation: 100/min per org
- Investigation: 20/min per org
- General API: 500/min per org
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

RATE_LIMITS: dict[str, tuple[int, int]] = {
    "webhook": (1000, 60),       # 1000 per 60 seconds
    "payment_initiate": (100, 60),
    "investigation": (20, 60),
    "default": (500, 60),
}


def get_endpoint_bucket(path: str) -> str:
    """Map request path to rate limit bucket."""
    if "/webhooks/" in path:
        return "webhook"
    if path.endswith("/initiate") or "/payments" in path and "POST" in path:
        return "payment_initiate"
    if "/investigations" in path:
        return "investigation"
    return "default"


async def check_rate_limit(
    redis_client: object,
    organization_id: str,
    bucket: str,
) -> tuple[bool, dict]:
    """
    Sliding window rate limit check using Redis.
    Returns (allowed, headers_dict).
    """
    if redis_client is None:
        # No Redis — allow all (Phase 7 requires Redis for rate limiting)
        return True, {"X-RateLimit-Limit": "unlimited", "X-RateLimit-Remaining": "unlimited"}

    limit, window = RATE_LIMITS.get(bucket, RATE_LIMITS["default"])
    key = f"rl:{organization_id}:{bucket}"
    now = int(time.time())
    window_start = now - window

    try:
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window * 2)
        results = await pipe.execute()
        count = results[2]

        allowed = count <= limit
        remaining = max(0, limit - count)

        return allowed, {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Window": str(window),
            "X-RateLimit-Bucket": bucket,
        }
    except Exception as e:
        logger.warning("Rate limit check failed (Redis error): %s", e)
        return True, {}  # Fail open — don't block on Redis errors
