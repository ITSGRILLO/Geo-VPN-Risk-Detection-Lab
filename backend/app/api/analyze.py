"""
api/analyze.py

/analyze route: thin controller. No business logic here. It calls the
geolocation, rate limiter, and risk engine services, then returns the
combined response. Blocked IPs still get a full response body (with
risk data) so the dashboard can render a "blocked" state instead of
just a bare error.
"""

from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.geolocation import get_geo_info, GeolocationError
from app.services.risk_engine import calculate_risk
from app.services.rate_limiter import rate_limiter

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest, request: Request):
    # Rate limiting always keys on the real connection address,
    # never on a client-supplied value, so it can't be bypassed
    # by changing the "ip" field in the request body.
    limiter_key = request.client.host if request.client else "unknown"

    # The body "ip" is only used for the geolocation lookup (lab/testing).
    # None -> ip-api.com resolves the caller's own public IP.
    lookup_ip = payload.ip

    count, newly_blocked = rate_limiter.check_and_block(limiter_key)
    is_blocked = newly_blocked or rate_limiter.is_blocked(limiter_key)

    try:
        geo = await get_geo_info(lookup_ip)
    except GeolocationError as exc:
        raise HTTPException(status_code=502, detail=f"Geolocation lookup failed: {exc}")

    risk_score, risk_level, breakdown = calculate_risk(
        geo=geo,
        requests_per_minute=count,
        browser_timezone=payload.browser_timezone,
    )

    # Being blocked always forces risk to HIGH, regardless of other
    # signals. Rate abuse alone is a strong enough signal on its own.
    if is_blocked:
        risk_level = "HIGH"

    response = AnalyzeResponse(
        ip=geo.ip,
        country=geo.country,
        city=geo.city,
        isp=geo.isp,
        asn=geo.asn,
        timezone=geo.timezone,
        browser_timezone=payload.browser_timezone,
        vpn=geo.is_hosting,
        proxy=geo.is_proxy,
        requests_per_minute=count,
        risk_score=risk_score,
        risk_level=risk_level,
        breakdown=breakdown,
    )

    if is_blocked:
        # 429 with the full body attached via detail, so the frontend
        # can parse and render it instead of a generic error.
        raise HTTPException(status_code=429, detail=response.model_dump())

    return response