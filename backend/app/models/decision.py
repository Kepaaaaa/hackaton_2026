"""Decision engine output (A.7). Owner: T0."""

from __future__ import annotations

from pydantic import AwareDatetime

from app.models.common import DecisionLevel, DecisionType, Evidence, IntentType, JourneyType, StrictModel


class ScoreBreakdown(StrictModel):
    intent_confidence: float
    timing_relevance: float
    usefulness: float
    eligibility: float
    financial_fit: float
    penalties: float
    weights: dict[str, float]
    total: float


class JourneyCandidate(StrictModel):
    journey: JourneyType
    driven_by: list[IntentType]
    score: float
    breakdown: ScoreBreakdown
    decision_type: DecisionType
    evidence: list[Evidence]


class SuppressedCandidate(StrictModel):
    journey: JourneyType
    rule: str
    reason: str
    score_before: float


class Decision(StrictModel):
    decision_type: DecisionType
    level: DecisionLevel
    primary: JourneyCandidate | None
    secondary: list[JourneyCandidate]  # max 2
    considered: list[JourneyCandidate]
    suppressed: list[SuppressedCandidate]
    reasons: list[str]
    decided_at: AwareDatetime
