"""
services/geolocation.py

Wraps the free ip-api.com geolocation API to resolve IP -> geo/network signals.

Docs: https://ip-api.com/docs/api:json
Free tier limit: 45 requests/minute per source IP (no API key required).

Includes a small in-memory TTL cache. Without it, a client that gets
rate-limited/blocked still triggers a real API call on every retry,
which burns the shared 45/min quota for no benefit — the result for
that IP hasn't changed in the last few minutes anyway.
"""

import ipaddress
import time
import httpx
from typing import Optional
from threading import Lock
from app.models.schemas import GeoInfo

IP_API_BASE_URL = "http://ip-api.com/json"
IP_API_FIELDS = "status,message,country,city,isp,as,proxy,hosting,timezone,query"

# Fields we ask ip-api.com to return, mapped 1:1 onto GeoInfo.
# "as" is the ASN + org string, e.g. "AS16509 Amazon.com, Inc."

CACHE_TTL_SECONDS = 300  # 5 minutes — geo/ASN data for an IP rarely changes faster than this.


class GeolocationError(Exception):
    """Raised when the geolocation provider fails or returns bad data."""


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP is in a private/reserved range (RFC 1918, loopback,
    link-local, etc.). These have no public geolocation data by design,
    so we reject them before wasting an API call on a guaranteed failure.
    """
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False  # Not a valid IP at all — let the provider reject it with a clear message.


class GeoCache:
    """
    Simple in-memory TTL cache keyed by resolved IP.

    Not persisted and not shared across processes — fine for the MVP's
    single-process local setup. If this ever runs behind multiple
    workers, swap the internals for Redis (SET with EX) and keep the
    same get/set interface so callers don't change.
    """

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, GeoInfo]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[GeoInfo]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            cached_at, geo = entry
            if time.time() - cached_at > self.ttl_seconds:
                del self._store[key]
                return None
            return geo

    def set(self, key: str, geo: GeoInfo) -> None:
        with self._lock:
            self._store[key] = (time.time(), geo)


# Single shared instance for the app.
_geo_cache = GeoCache()


async def get_geo_info(ip: Optional[str] = None) -> GeoInfo:
    """
    Resolve geolocation + network signals for an IP address, using a
    5-minute in-memory cache to avoid re-hitting the provider for
    repeat lookups of the same IP.

    Args:
        ip: IPv4/IPv6 address to look up. If None, ip-api.com resolves
            the caller's own public IP (useful for local testing).
            Note: a None lookup is never cached, since "my own IP"
            is a query about the caller, not about a fixed IP key.

    Returns:
        GeoInfo with country, city, isp, asn, proxy/hosting flags, timezone.

    Raises:
        GeolocationError: on a private/invalid IP, network failure,
            timeout, or a non-success response from the provider.
    """
    if ip and is_private_ip(ip):
        raise GeolocationError(
            f"'{ip}' is a private/reserved IP address and has no public "
            "geolocation data. Try a public IP instead."
        )

    if ip:
        cached = _geo_cache.get(ip)
        if cached is not None:
            return cached

    target = ip or ""  # empty string -> ip-api.com resolves caller's IP
    url = f"{IP_API_BASE_URL}/{target}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params={"fields": IP_API_FIELDS})
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise GeolocationError("Geolocation provider timed out") from exc
    except httpx.HTTPError as exc:
        raise GeolocationError(f"Geolocation provider request failed: {exc}") from exc

    if data.get("status") != "success":
        # ip-api.com returns status: "fail" with a "message" field
        # (e.g. "invalid query", "private range", rate-limit messages).
        raise GeolocationError(data.get("message", "Unknown geolocation error"))

    geo = GeoInfo(
        ip=data.get("query", target),
        country=data.get("country", "Unknown"),
        city=data.get("city", "Unknown"),
        isp=data.get("isp", "Unknown"),
        asn=data.get("as", "Unknown"),
        timezone=data.get("timezone", "Unknown"),
        is_proxy=bool(data.get("proxy", False)),
        is_hosting=bool(data.get("hosting", False)),
    )

    if ip:
        _geo_cache.set(ip, geo)

    return geo