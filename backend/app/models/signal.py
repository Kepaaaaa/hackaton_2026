"""Signals: interpretations of facts (A.7). Owner: T0."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field

from app.models.common import SignalType, StrictModel


class Signal(StrictModel):
    type: SignalType
    strength: float = Field(ge=0, le=1)
    timestamp: AwareDatetime
    expires_at: AwareDatetime | None
    source: Literal["event", "pattern"]
    source_event_ids: list[str]
    description: str  # "Airline payment of €420 (Brussels Airlines)"
