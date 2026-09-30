"""Exception handlers and error JSON `{"error": {"code", "message"}}` (A.10).

Rules: neutral messages, no stack traces, and 422 responses never echo the raw input.

Owner: T5.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.repositories.base import EventLimitExceeded

NOT_FOUND_MESSAGE = "Resource not found."

_HTTP_CODES = {
    400: "BAD_REQUEST",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "TOO_MANY_EVENTS",
}


class NotFoundError(Exception):
    """Unknown customer, scenario or step. Always rendered as a neutral 404."""

    def __init__(self, message: str = NOT_FOUND_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


def error_response(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


GENERIC_VALIDATION_MESSAGE = "Invalid value."
EXTRA_FIELD_LOC = "<extra field>"


def _safe_detail(err: dict) -> dict:
    """Only location and message, never `input` or `ctx`. Pydantic sometimes quotes the input
    in `msg` (e.g. an unknown union tag) or in `loc` (the name of an extra field): both are masked."""
    loc = [str(part) for part in err.get("loc", ())]
    if err.get("type") == "extra_forbidden" and loc:
        loc[-1] = EXTRA_FIELD_LOC
    msg = str(err.get("msg", GENERIC_VALIDATION_MESSAGE))
    raw = err.get("input")
    if isinstance(raw, str) and raw and raw in msg:
        msg = GENERIC_VALIDATION_MESSAGE
    elif isinstance(raw, dict) and any(isinstance(v, str) and v and v in msg for v in raw.values()):
        msg = GENERIC_VALIDATION_MESSAGE
    return {"loc": loc, "msg": msg}


def _safe_validation_details(exc: RequestValidationError) -> list[dict]:
    return [_safe_detail(err) for err in exc.errors()[:20]]


async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    return error_response(404, "NOT_FOUND", exc.message)


async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "The request is invalid.", _safe_validation_details(exc))


async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    message = NOT_FOUND_MESSAGE if exc.status_code == 404 else str(exc.detail)
    return error_response(exc.status_code, code, message)


async def _event_limit(_: Request, __: EventLimitExceeded) -> JSONResponse:
    return error_response(429, "TOO_MANY_EVENTS", "The event log for this customer is full.")


async def _unexpected(_: Request, __: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(EventLimitExceeded, _event_limit)
    app.add_exception_handler(Exception, _unexpected)
