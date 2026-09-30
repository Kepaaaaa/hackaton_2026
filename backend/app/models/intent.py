"""Intents: probable needs, several at once (A.7). Owner: T0."""

from __future__ import annotations

from app.models.common import Evidence, IntentType, MomentType, StrictModel


class Intent(StrictModel):
    type: IntentType
    confidence: float
    related_moments: list[MomentType]
    evidence: list[Evidence]
