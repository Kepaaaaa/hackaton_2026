"""FastAPI application. Owner: T5 (T0 created the minimal app with /health).

`create_app(settings, service)` lets tests inject their own settings and service
(e.g. a fixed clock). Without a service, one is wired from the seed files at startup.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api import customers, events, feedback, scenarios
from app.core.clock import SystemClock
from app.core.config import Settings, get_settings
from app.core.errors import error_response, register_error_handlers
from app.services.personalization_service import PersonalizationService

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
]
NO_STORE_PREFIXES = ("/customers", "/scenarios")

TAGS = [
    {"name": "customers", "description": "Read a customer's state: generic overview, context, intents, decision, experience."},
    {"name": "events", "description": "Post a fact (transaction, page view, simulation, search...) and get the recomputed experience."},
    {"name": "feedback", "description": "Customer control: feedback on journeys and personalization consent."},
    {"name": "demo", "description": "Demo-only (KBC_DEMO_MODE=true): scripted scenarios and reset."},
    {"name": "system", "description": "Health check."},
]


class SecurityHeadersMiddleware:
    """Adds A.10 security headers to every response, and `Cache-Control: no-store` on customer data."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        no_store = scope["path"].startswith(NO_STORE_PREFIXES)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [h for h in message.get("headers", []) if h[0].lower() != b"cache-control" or not no_store]
                headers += SECURITY_HEADERS
                if no_store:
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """Rejects request bodies above `max_bytes` with 413, whether or not Content-Length is sent."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return

        too_large = error_response(413, "PAYLOAD_TOO_LARGE", "The request body is too large.")
        for name, value in scope.get("headers", []):
            if name == b"content-length" and (not value.isdigit() or int(value) > self.max_bytes):
                await too_large(scope, receive, send)
                return

        # Buffer the (small) body, counting bytes, then replay it downstream.
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await too_large(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None, service: PersonalizationService | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.service is None:
            app.state.service = PersonalizationService.from_seed(
                SystemClock(), max_events_per_customer=settings.max_events_per_customer
            )
        yield

    app = FastAPI(
        title="KBC Context API",
        description=(
            "Event-driven personalization for the KBC challenge (Tectonic Hackathon). "
            "Events -> signals -> context -> intents -> decision -> journey -> experience. "
            "Deterministic rules, full evidence, and sometimes the best recommendation is none. "
            "Synthetic data only."
        ),
        version="0.1.0",
        openapi_tags=TAGS,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.service = service

    register_error_handlers(app)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(customers.router)
    app.include_router(events.router)
    app.include_router(feedback.router)
    app.include_router(scenarios.router)

    @app.get("/health", tags=["system"], summary="Liveness check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
