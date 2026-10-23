# Geo & VPN Risk Detection Lab

A local, educational lab exploring how services infer whether an incoming
IP address is trustworthy — geolocation, VPN/proxy detection, and simple
risk scoring — built as a learning project, not a production security tool.

## Why this exists

Platforms that care about fraud, ban evasion, or geo-restriction bypass
often need to answer: *"is this request coming from where/what it claims
to be?"* This project explores the signals used to answer that question,
and shows how they combine into a single risk score.

This lab analyzes **only your own requests and public test IPs** — it
does not attempt to bypass or defeat any real service's detection.

## Architecture
Browser (React) → FastAPI → ip-api.com (geolocation)
│
├── Risk Engine (scoring)
└── Rate Limiter (in-memory, sliding window)


- **Frontend:** React + Vite, single dashboard page
- **Backend:** FastAPI (Python), thin route → service layer → response
- **Geolocation provider:** [ip-api.com](https://ip-api.com) free tier
  (45 requests/minute, no API key)
- **State:** in-memory only (rate limiter counters, geolocation cache) —
  nothing persisted to disk in this version

## Signals collected

| Signal | Source | What it means |
|---|---|---|
| Country, city, ISP, ASN | ip-api.com | Basic geolocation + network owner |
| `hosting` flag | ip-api.com | IP belongs to a datacenter/cloud provider (proxy for "VPN-like") |
| `proxy` flag | ip-api.com | IP is a known open proxy |
| ASN keyword match | Local heuristic | ASN/org string contains known hosting-provider names (AWS, DigitalOcean, OVH, etc.) as a backup signal |
| Browser timezone vs. IP timezone | Client + server | Flags a mismatch between where the IP claims to be and what the browser reports |
| Requests per minute | Local rate limiter | Detects request bursts from a single client |

## Risk scoring

Each triggered signal adds points to a running total:

| Signal | Points |
|---|---|
| VPN/hosting detected | +40 |
| Proxy detected | +35 |
| Datacenter ASN (keyword match, no hosting flag) | +25 |
| Timezone mismatch | +20 |
| Too many requests (>10/min) | +30 |

| Score | Level |
|---|---|
| 0–29 | LOW |
| 30–59 | MEDIUM |
| 60+ | HIGH |

Being rate-limited (blocked) always forces the level to HIGH regardless
of other signals — rate abuse is treated as a strong signal on its own.

**These weights and thresholds are this lab's own invented scoring rules
for learning purposes** — they are not a claim about how any real
platform (financial, gaming, employment, etc.) actually scores risk.

## Rate limiting

- Sliding 60-second window, max 10 requests per client
- Keyed on the real server-side connection IP (`request.client.host`),
  never on a client-supplied value — this was a deliberate fix after an
  early version accidentally let a client bypass the limiter by
  changing the `ip` field in the request body
- Exceeding the limit returns HTTP 429, with the full risk analysis
  still attached in the response body so the dashboard can render a
  "blocked" state rather than a bare error
- Blocks and counters are in-memory only and reset on server restart

## Running it locally

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Known limitations

- **Private/reserved IPs (e.g. `10.x.x.x`, `192.168.x.x`) cannot be
  analyzed** — they have no public geolocation data by design, and the
  API rejects them with a clear error rather than a confusing failure.
- **Timezone mismatch is a strict string comparison** of IANA zone
  names, not a "plausibility" check. A genuine traveler, or someone
  with their system clock set to the wrong region, will also trigger
  this signal — it's a real false-positive risk, stated openly here
  rather than hidden.
- **Rate limiting and the geolocation cache are in-memory and
  single-process.** They reset on restart and wouldn't work correctly
  behind multiple server workers or instances. A production version
  would move this state to Redis.
- **ASN heuristic keyword list is not exhaustive.** It catches common
  major cloud/hosting providers but will miss smaller or regional
  hosting companies not on the list.
- **No authentication, persistence, or historical logging of past
  analyses** — this is a single-request lab tool, not a monitoring
  system.
- Uses the free tier of ip-api.com (HTTP only, 45 req/min limit) —
  fine for local testing, not suitable for production traffic volume.

## What I'd improve next

- Move rate-limiter and cache state to Redis for multi-instance support
- Add a persisted log of past analyses (SQLite) for a history view
- Add device/browser fingerprint signals alongside timezone
- Add unit tests for the risk engine's scoring boundaries
- Swap the free geolocation tier for a paid provider with a dedicated
  VPN-detection flag (rather than inferring it from `hosting`)

## Disclaimer

Built as a personal cybersecurity learning project to understand how
geolocation, network classification, and rate-limiting signals combine
in real-world risk scoring systems. Not intended for production use,
and not a claim about the internals of any specific commercial platform.