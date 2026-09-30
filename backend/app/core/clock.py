"""Injectable clock. The only place allowed to call `datetime.now()`. Owner: T0."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Deterministic clock for tests and demos."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._at = at

    def now(self) -> datetime:
        return self._at

    def set(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._at = at

    def advance(self, **kwargs: float) -> None:
        self._at += timedelta(**kwargs)
