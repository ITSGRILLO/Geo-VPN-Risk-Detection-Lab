"""
services/risk_engine.py

Pure scoring logic: takes resolved signals and produces a risk score + level.
No HTTP calls, no DB access — this stays a plain function so it's trivially
unit-testable in isolation.
"""

from app.models.schemas import GeoInfo, RiskBreakdown

# Scoring weights — tunable constants, not magic numbers scattered in logic.
SCORE_VPN = 40
SCORE_PROXY = 35
SCORE_DATACENTER_ASN = 25
SCORE_TIMEZONE_MISMATCH = 20
SCORE_TOO_MANY_REQUESTS = 30

# Risk level thresholds
LOW_MAX = 29
MEDIUM_MAX = 59

# Keywords found in ASN/org strings that indicate hosting/datacenter infra
# rather than a residential ISP. Not exhaustive — this is a heuristic layer
# on top of ip-api.com's own `hosting` flag, not a replacement for it.
DATACENTER_KEYWORDS = [
    "amazon", "aws", "digitalocean", "ovh", "hetzner",
    "google cloud", "gcp", "azure", "linode", "vultr",
    "cloudflare", "leaseweb", "contabo",
]


def is_datacenter_asn(asn: str) -> bool:
    """Check the ASN/org string for known hosting-provider keywords."""
    asn_lower = asn.lower()
    return any(keyword in asn_lower for keyword in DATACENTER_KEYWORDS)


def score_to_level(score: int) -> str:
    """Map a numeric score to a risk level bucket."""
    if score <= LOW_MAX:
        return "LOW"
    if score <= MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def has_timezone_mismatch(ip_timezone: str, browser_timezone: str | None) -> bool:
    """
    Compare the IP's resolved timezone against the browser-reported one.

    This is a strict IANA-zone string comparison, which is a deliberate
    simplification: two different zones can share the same UTC offset
    (e.g. a VPN in a neighboring country), so this catches obvious
    mismatches but can miss subtler ones, and can also false-positive
    for a traveler whose IP genuinely differs from home settings.
    """
    if not browser_timezone:
        return False
    return ip_timezone.strip().lower() != browser_timezone.strip().lower()


def calculate_risk(
    geo: GeoInfo,
    requests_per_minute: int,
    browser_timezone: str | None = None,
) -> tuple[int, str, RiskBreakdown]:
    """
    Calculate a risk score from resolved signals.

    Args:
        geo: resolved geolocation/network info for the IP.
        requests_per_minute: current request rate for this IP.
        browser_timezone: IANA timezone reported by the client browser,
            compared against the IP's timezone. None skips this check.

    Returns:
        (risk_score, risk_level, breakdown) — breakdown shows which
        individual signals contributed, for transparency in the dashboard.
    """
    breakdown = RiskBreakdown()

    if geo.is_proxy:
        breakdown.proxy_detected = SCORE_PROXY

    # ip-api.com's `hosting` flag and our own ASN keyword check both point
    # at "this looks like a VPN/datacenter exit node" — treat hosting=True
    # as the VPN signal since ip-api.com doesn't separately flag VPNs.
    if geo.is_hosting:
        breakdown.vpn_detected = SCORE_VPN
    elif is_datacenter_asn(geo.asn):
        breakdown.datacenter_asn = SCORE_DATACENTER_ASN

    if has_timezone_mismatch(geo.timezone, browser_timezone):
        breakdown.timezone_mismatch = SCORE_TIMEZONE_MISMATCH

    if requests_per_minute > 10:
        breakdown.too_many_requests = SCORE_TOO_MANY_REQUESTS

    total_score = (
        breakdown.vpn_detected
        + breakdown.proxy_detected
        + breakdown.datacenter_asn
        + breakdown.timezone_mismatch
        + breakdown.too_many_requests
    )

    return total_score, score_to_level(total_score), breakdown