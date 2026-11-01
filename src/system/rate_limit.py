"""Rate limiting configuration for the application.

This module configures rate limiting using slowapi, with default limits
defined in the application settings. Rate limits are applied based on
remote IP addresses.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config.settings import settings


def get_client_identifier(request: Request) -> str:
    """Identify client by Authorization token, forwarded proxy IP, or remote address.

    Ensures that multiple concurrent customers (behind proxies, NATs, or distinct sessions)
    do not share the same rate-limit bucket and get blocked.
    """
    auth = request.headers.get("authorization")
    if auth:
        # Rate limit per authenticated user/session token
        return f"auth:{auth.strip()[-32:]}"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return get_remote_address(request) or "127.0.0.1"


# Initialize rate limiter with multi-client key function and enabled flag
limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=settings.RATE_LIMIT_DEFAULT,
    enabled=settings.RATE_LIMIT_ENABLED,
)
