"""
main.py — FastAPI app entrypoint.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.analyze import router as analyze_router

app = FastAPI(
    title="Geo & VPN Risk Detection Lab",
    description="Educational lab: IP geolocation, VPN/proxy heuristics, and risk scoring.",
    version="0.1.0",
)

# Restrictive CORS for local dev — tighten origins list before any
# real deployment; "*" is fine only because this stays local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server default
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(analyze_router)


@app.get("/health")
async def health():
    return {"status": "ok"}