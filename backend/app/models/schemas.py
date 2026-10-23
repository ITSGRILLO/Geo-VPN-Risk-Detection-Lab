"""
models/schemas.py

Pydantic models defining the request/response contracts for the API.
Keeping these in one file means the /analyze response shape is defined
in exactly one place, and every service returns objects that match it.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    """Request body for /analyze."""
    ip: Optional[str] = Field(
        default=None,
        description="IPv4/IPv6 address to analyze. Omit to use your own public IP.",
    )
    browser_timezone: Optional[str] = Field(
        default=None,
        description=(
            "IANA timezone reported by the browser "
            "(Intl.DateTimeFormat().resolvedOptions().timeZone), e.g. 'Africa/Nairobi'. "
            "Compared against the IP's timezone to flag a geo/browser signal mismatch."
        ),
    )


class GeoInfo(BaseModel):
    """Raw signals resolved from the geolocation provider."""
    ip: str
    country: str
    city: str
    isp: str
    asn: str
    timezone: str
    is_proxy: bool
    is_hosting: bool


class RiskBreakdown(BaseModel):
    """Individual scoring contributions, so the dashboard/README can show
    *why* a score was assigned, not just the final number."""
    vpn_detected: int = 0
    proxy_detected: int = 0
    datacenter_asn: int = 0
    timezone_mismatch: int = 0
    too_many_requests: int = 0


class AnalyzeResponse(BaseModel):
    """Full response returned by /analyze — matches the MVP spec."""
    ip: str
    country: str
    city: str
    isp: str
    asn: str
    timezone: str
    browser_timezone: Optional[str] = None
    vpn: bool
    proxy: bool
    requests_per_minute: int
    risk_score: int
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH"
    breakdown: RiskBreakdown