"""FastAPI application. Owner: T5 (T0 created the minimal app with /health)."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="KBC Context API",
    description="Event-driven personalization: events -> signals -> context -> intents -> decision -> experience.",
    version="0.1.0",
)


@app.get("/health", tags=["system"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}
