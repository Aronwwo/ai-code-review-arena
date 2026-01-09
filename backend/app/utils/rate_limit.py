"""Rate limiting utilities."""
import time
from fastapi import HTTPException, Request, status
from app.config import settings
from app.utils.cache import cache

# In-memory fallback for rate limiting (if Redis unavailable)
_memory_rate_limit: dict[str, list[float]] = {}


def check_rate_limit(request: Request, user_id: int | None = None, limit: int | None = None):
    """Check if request is within rate limit.

    Args:
        request: FastAPI request
        user_id: User ID (if authenticated)
        limit: Custom limit (default from settings)

    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.rate_limit_enabled:
        return

    # Determine rate limit key
    if user_id:
        key = f"rate_limit:user:{user_id}:{request.url.path}"
    else:
        key = f"rate_limit:ip:{request.client.host}:{request.url.path}"

    # Determine limit
    rate_limit = limit or settings.rate_limit_per_minute
    window = 60  # 1 minute window

    current_time = time.time()

    # Try Redis first
    if cache.redis_client:
        try:
            # Use Redis sorted set for sliding window
            cache.redis_client.zadd(key, {str(current_time): current_time})
            cache.redis_client.zremrangebyscore(key, 0, current_time - window)
            cache.redis_client.expire(key, window)

            count = cache.redis_client.zcard(key)

            if count > rate_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {rate_limit} requests per minute."
                )
            return

        except Exception as e:
            # Fall through to memory-based rate limiting
            print(f"Redis rate limit error: {e}")

    # Fallback to in-memory rate limiting
    if key not in _memory_rate_limit:
        _memory_rate_limit[key] = []

    # Remove old timestamps
    _memory_rate_limit[key] = [
        ts for ts in _memory_rate_limit[key]
        if ts > current_time - window
    ]

    # Add current timestamp
    _memory_rate_limit[key].append(current_time)

    # Check limit
    if len(_memory_rate_limit[key]) > rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {rate_limit} requests per minute."
        )


def rate_limit_middleware():
    """Middleware for rate limiting."""
    async def middleware(request: Request, call_next):
        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Extract user_id if authenticated (from token if present)
        user_id = None
        # Note: In production, you'd decode the JWT token here

        # Apply rate limiting
        try:
            check_rate_limit(request, user_id)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        response = await call_next(request)
        return response

    return middleware
