"""Decision weights, thresholds, timing curve, suppression rules, feedback windows (A.9).

Owner: T4.

Everything the Decision Engine weighs lives here as data. The engine is a generic loop:
candidates = intents x journeys -> score breakdown -> suppression rules in order -> rank.
"""

from __future__ import annotations

from pydantic import Field

from app.models.common import DecisionType, JourneyKind, MomentType
from app.rules.schema import DecisionThresholds, DecisionWeights, RuleModel, SuppressionRule


class TimingCurve(RuleModel):
    """timing = 1.0 while age/lifetime <= full_until, then linear down to `floor` at 1.0."""

    full_until: float = 0.33
    floor: float = 0.3
    without_moment: float = 0.5  # intent driven by signals only, no ACTIVE moment behind it


class FeedbackWindows(RuleModel):
    dismissed_days: int = 30  # NOT_RELEVANT -> suppressed (FEEDBACK_DISMISSED)
    later_days: int = 7  # LATER -> penalty only
    later_penalty: float = 0.25


class FinancialFit(RuleModel):
    """safety = w_p * clamp(projected / spending) + w_b * clamp(buffer / target_months)."""

    projected_weight: float = 0.6
    buffer_weight: float = 0.4
    buffer_target_months: float = 6.0
    spending_floor: float = 1.0


class DecisionTypeRule(RuleModel):
    default: DecisionType
    urgent: DecisionType | None = None


class DecisionRules(RuleModel):
    weights: DecisionWeights = DecisionWeights()
    thresholds: DecisionThresholds = DecisionThresholds()
    timing: TimingCurve = TimingCurve()
    feedback: FeedbackWindows = FeedbackWindows()
    financial_fit: FinancialFit = FinancialFit()
    # usefulness *= (1 - covered_usefulness_factor * covered_ratio)
    covered_usefulness_factor: float = Field(0.5, ge=0, le=1)
    suppression_rules: list[SuppressionRule] = []
    decision_types: dict[JourneyKind, DecisionTypeRule] = {}
    all_covered_decision_type: DecisionType = DecisionType.SHOW_SERVICE
    passive_decision_type: DecisionType = DecisionType.PASSIVE_PERSONALIZATION


DECISION_WEIGHTS = DecisionWeights()
DECISION_THRESHOLDS = DecisionThresholds()

# Evaluated in order; the first matching rule suppresses the candidate.
SUPPRESSION_RULES: list[SuppressionRule] = [
    SuppressionRule(id="NO_CONSENT", description="Personalization is turned off by the customer."),
    SuppressionRule(
        id="LOW_CONFIDENCE",
        description="The need behind this journey is not clear enough yet.",
        params={"min_intent_confidence": DECISION_THRESHOLDS.low_confidence},
    ),
    SuppressionRule(
        id="FEEDBACK_DISMISSED",
        description="The customer said this is not relevant.",
        params={"window_days": FeedbackWindows().dismissed_days},
    ),
    SuppressionRule(
        id="CASHFLOW_RISK",
        description="Cash flow is under pressure: commercial journeys are paused.",
        params={
            "moment": MomentType.CASHFLOW_PRESSURE.value,
            "min_moment_confidence": 0.70,
            # Same thresholds as the LOW_PROJECTED_BALANCE pattern signal (A.9).
            "low_projected_abs": 500.0,
            "low_projected_ratio": 0.3,
            "suppress_kinds": [JourneyKind.COMMERCIAL.value],
        },
    ),
    SuppressionRule(id="ALREADY_COVERED", description="Every product of this journey is already owned."),
    SuppressionRule(id="NOT_ELIGIBLE", description="An eligibility condition is not met."),
]

DECISION_TYPES: dict[JourneyKind, DecisionTypeRule] = {
    JourneyKind.SUPPORT: DecisionTypeRule(default=DecisionType.SHOW_GUIDANCE, urgent=DecisionType.SHOW_WARNING),
    JourneyKind.GUIDANCE: DecisionTypeRule(default=DecisionType.SHOW_JOURNEY),
    JourneyKind.COMMERCIAL: DecisionTypeRule(default=DecisionType.SHOW_JOURNEY),
}

DECISION_RULES = DecisionRules(
    weights=DECISION_WEIGHTS,
    thresholds=DECISION_THRESHOLDS,
    suppression_rules=SUPPRESSION_RULES,
    decision_types=DECISION_TYPES,
)

# Short English sentences for `Decision.reasons` (formatted by the engine).
REASONS = {
    "primary": "{journey} selected with score {score:.2f} ({level}).",
    "driven_by": "Driven by {intent} (relevance-weighted confidence {confidence:.0%}).",
    "secondary": "Also relevant: {journey} ({score:.2f}).",
    "suppressed": "{journey} not shown ({rule}): {reason}",
    "wait": "Something may be starting ({moments}); waiting for clearer signals before acting.",
    "wait_timing": "The best option ({journey}) is not timely enough; waiting.",
    "no_action": "No journey is relevant enough right now (best score below {threshold:.2f}). Nothing to show.",
}
