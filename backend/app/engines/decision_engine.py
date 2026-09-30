"""Decision Engine: intents x journeys -> scored, suppressed, ranked decision. Owner: T4.

Generic loop, no journey/moment/intent names in code:
1. build one candidate per journey serving at least one intent,
2. compute its score breakdown (A.9 weights),
3. apply the ordered suppression rules (registered functions, parameters from rules),
4. rank; pick primary / secondary; derive level and decision type.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.common import (
    DecisionLevel,
    DecisionType,
    EventType,
    Evidence,
    FeedbackType,
    JourneyKind,
    JourneyType,
    MomentStatus,
    ProductType,
)
from app.models.context import ActiveMoment
from app.models.customer import Customer
from app.models.decision import Decision, JourneyCandidate, ScoreBreakdown, SuppressedCandidate
from app.models.event import CustomerEvent
from app.models.intent import Intent
from app.models.journey import JourneyDef
from app.models.snapshot import FinancialSnapshot
from app.rules.decisions import DECISION_RULES, REASONS, DecisionRules
from app.rules.journeys import JOURNEYS


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _r(x: float) -> float:
    return round(x, 4)


def product_coverage(journey: JourneyDef, owned: set[ProductType]) -> tuple[int, int]:
    """(covered, total) over the journey's actions that carry a product."""
    products = [a.product for a in journey.actions if a.product is not None]
    return sum(1 for p in products if p in owned), len(products)


@dataclass
class _FeedbackState:
    dismissed_days_ago: dict[JourneyType, float] = field(default_factory=dict)
    later_days_ago: dict[JourneyType, float] = field(default_factory=dict)


@dataclass
class _Ctx:
    customer: Customer
    snapshot: FinancialSnapshot
    moments: Sequence[ActiveMoment]
    owned: set[ProductType]
    feedback: _FeedbackState
    now: datetime


@dataclass
class _Draft:
    journey: JourneyDef
    driven_by: list[tuple[Intent, float]]  # (intent, confidence x relevance), strongest first
    breakdown: ScoreBreakdown
    evidence: list[Evidence]
    failed_condition: str | None


# --- Suppression rules: id -> function(draft, ctx, params) -> reason | None ---------------


def _no_consent(d: _Draft, ctx: _Ctx, p: Mapping[str, Any]) -> str | None:
    return None if ctx.customer.consent.personalization else "Personalization is turned off by the customer."


def _low_confidence(d: _Draft, ctx: _Ctx, p: Mapping[str, Any]) -> str | None:
    threshold = float(p.get("min_intent_confidence", 0.40))
    ic = d.breakdown.intent_confidence
    return f"Intent confidence {ic:.2f} is below {threshold:.2f}." if ic < threshold else None


def _feedback_dismissed(d: _Draft, ctx: _Ctx, p: Mapping[str, Any]) -> str | None:
    days = ctx.feedback.dismissed_days_ago.get(d.journey.type)
    if days is None or days > float(p.get("window_days", 30)):
        return None
    return f"The customer marked this as not relevant {int(days)} day(s) ago."


def _cashflow_risk(d: _Draft, ctx: _Ctx, p: Mapping[str, Any]) -> str | None:
    if d.journey.kind.value not in p.get("suppress_kinds", []):
        return None
    moment_hit = any(
        m.type.value == p.get("moment") and m.confidence >= float(p.get("min_moment_confidence", 0.70))
        for m in ctx.moments
    )
    s = ctx.snapshot
    spending = max(s.avg_monthly_spending, 1.0)
    projected = s.projected_balance_before_next_income
    low_projected = projected < float(p.get("low_projected_abs", 500)) or projected < float(
        p.get("low_projected_ratio", 0.3)
    ) * spending
    if moment_hit or low_projected:
        return "Your balance may run low before your next income, so offers are paused."
    return None


def _already_covered(d: _Draft, ctx: _Ctx, p: Mapping[str, Any]) -> str | None:
    covered, total = product_coverage(d.journey, ctx.owned)
    if total and covered == total and len(d.journey.actions) == total:
        return "Every product of this journey is already owned."
    return None


def _not_eligible(d: _Draft, ctx: _Ctx, p: Mapping[str, Any]) -> str | None:
    return f"Eligibility condition not met: {d.failed_condition}." if d.failed_condition else None


SUPPRESSION_FUNCTIONS: dict[str, Callable[[_Draft, _Ctx, Mapping[str, Any]], str | None]] = {
    "NO_CONSENT": _no_consent,
    "LOW_CONFIDENCE": _low_confidence,
    "FEEDBACK_DISMISSED": _feedback_dismissed,
    "CASHFLOW_RISK": _cashflow_risk,
    "ALREADY_COVERED": _already_covered,
    "NOT_ELIGIBLE": _not_eligible,
}


class DecisionEngine:
    def __init__(
        self,
        rules: DecisionRules | None = None,
        journeys: Mapping[JourneyType, JourneyDef] | None = None,
    ) -> None:
        self.rules = rules or DECISION_RULES
        self.journeys = journeys if journeys is not None else JOURNEYS
        unknown = [r.id for r in self.rules.suppression_rules if r.id not in SUPPRESSION_FUNCTIONS]
        if unknown:
            raise ValueError(f"unknown suppression rules: {unknown}")

    # --- public ---------------------------------------------------------------------------

    def decide(
        self,
        customer: Customer,
        snapshot: FinancialSnapshot,
        moments: Sequence[ActiveMoment],
        intents: Sequence[Intent],
        events: Sequence[CustomerEvent],
        now: datetime,
    ) -> Decision:
        ctx = _Ctx(
            customer=customer,
            snapshot=snapshot,
            moments=moments,
            owned=set(customer.owned_products()),
            feedback=self._read_feedback(events, now),
            now=now,
        )
        drafts = [d for j in self.journeys.values() if (d := self._draft(j, intents, ctx)) is not None]

        considered: list[JourneyCandidate] = []
        suppressed: list[SuppressedCandidate] = []
        for d in drafts:
            hit = self._first_suppression(d, ctx)
            if hit:
                suppressed.append(
                    SuppressedCandidate(journey=d.journey.type, rule=hit[0], reason=hit[1], score_before=d.breakdown.total)
                )
            else:
                considered.append(self._candidate(d, ctx))

        considered.sort(key=lambda c: (-c.score, c.journey.value))
        suppressed.sort(key=lambda s: (-s.score_before, s.journey.value))
        return self._choose(considered, suppressed, moments, now)

    # --- steps ----------------------------------------------------------------------------

    def _read_feedback(self, events: Sequence[CustomerEvent], now: datetime) -> _FeedbackState:
        """Latest feedback per journey decides (a later USEFUL cancels an earlier NOT_RELEVANT)."""
        latest: dict[JourneyType, CustomerEvent] = {}
        for e in events:
            if e.type != EventType.RECOMMENDATION_FEEDBACK or e.timestamp > now:
                continue
            j = e.data.journey
            if j not in latest or e.timestamp >= latest[j].timestamp:
                latest[j] = e
        state = _FeedbackState()
        for j, e in latest.items():
            days = (now - e.timestamp).total_seconds() / 86400
            if e.data.feedback == FeedbackType.NOT_RELEVANT:
                state.dismissed_days_ago[j] = days
            elif e.data.feedback == FeedbackType.LATER:
                state.later_days_ago[j] = days
        return state

    def _draft(self, journey: JourneyDef, intents: Sequence[Intent], ctx: _Ctx) -> _Draft | None:
        driven = sorted(
            ((i, i.confidence * journey.serves_intents[i.type]) for i in intents if i.type in journey.serves_intents),
            key=lambda x: (-x[1], x[0].type.value),
        )
        driven = [(i, v) for i, v in driven if v > 0]
        if not driven:
            return None
        rules, w = self.rules, self.rules.weights
        top_intent, intent_conf = driven[0]
        intent_conf = _clamp(intent_conf)

        timing, timing_moment = self._timing([i for i, _ in driven], ctx)

        covered, total = product_coverage(journey, ctx.owned)
        covered_ratio = covered / total if total else 0.0
        usefulness = _clamp(journey.usefulness * (1 - rules.covered_usefulness_factor * covered_ratio))

        values = ctx.snapshot.model_dump()
        failed = next((c for c in journey.eligibility if not c.evaluate(values, ctx.owned)), None)
        eligibility = 0.0 if failed else 1.0

        safety = self._safety(ctx.snapshot)
        financial_fit = 1 - safety if journey.kind == JourneyKind.SUPPORT else safety

        later_days = ctx.feedback.later_days_ago.get(journey.type)
        penalty = rules.feedback.later_penalty if later_days is not None and later_days <= rules.feedback.later_days else 0.0

        parts = {
            "intent_confidence": intent_conf,
            "timing_relevance": timing,
            "usefulness": usefulness,
            "eligibility": eligibility,
            "financial_fit": financial_fit,
        }
        weights = w.as_dict()
        contributions = {k: _r(weights[k] * v) for k, v in parts.items()}
        total = _r(sum(contributions.values()) - penalty)
        breakdown = ScoreBreakdown(
            **{k: _r(v) for k, v in parts.items()}, penalties=_r(penalty), weights=weights, total=total
        )

        evidence = [
            Evidence(kind="rule", ref=top_intent.type.value, contribution=contributions["intent_confidence"],
                     detail=f"Need {top_intent.type.value} at {top_intent.confidence:.0%} confidence, "
                            f"{journey.serves_intents[top_intent.type]:.0%} relevant for this journey."),
            Evidence(kind="moment", ref=timing_moment.type.value if timing_moment else "timing",
                     contribution=contributions["timing_relevance"],
                     detail=(f"{timing_moment.type.value} detected "
                             f"{max(0, (ctx.now - timing_moment.detected_at).days)} day(s) ago."
                             if timing_moment else "No active life moment behind this need.")),
            Evidence(kind="rule", ref="usefulness", contribution=contributions["usefulness"],
                     detail=f"Journey usefulness {usefulness:.2f}"
                            + (f" ({covered}/{total} products already owned)." if covered else ".")),
            Evidence(kind="rule", ref="eligibility", contribution=contributions["eligibility"],
                     detail="Eligible." if not failed else f"Not eligible: {failed.field} {failed.op} {failed.value}."),
            Evidence(kind="financial", ref="financial_fit", contribution=contributions["financial_fit"],
                     detail=f"Financial safety {safety:.2f} "
                            f"({ctx.snapshot.emergency_buffer_months:.1f} months of buffer)."),
        ]
        evidence += [
            Evidence(kind="product", ref=a.product.value, contribution=0.0, detail=f"Already owns {a.product.value}.")
            for a in journey.actions
            if a.product is not None and a.product in ctx.owned
        ]
        if penalty:
            evidence.append(Evidence(kind="feedback", ref=FeedbackType.LATER.value, contribution=-_r(penalty),
                                     detail=f"The customer asked to see this later ({int(later_days)} day(s) ago)."))

        return _Draft(
            journey=journey,
            driven_by=driven,
            breakdown=breakdown,
            evidence=evidence,
            failed_condition=f"{failed.field} {failed.op} {failed.value}" if failed else None,
        )

    def _timing(self, intents: Sequence[Intent], ctx: _Ctx) -> tuple[float, ActiveMoment | None]:
        related = {m for i in intents for m in i.related_moments}
        active = [m for m in ctx.moments if m.type in related and m.status == MomentStatus.ACTIVE]
        curve = self.rules.timing
        if not active:
            return curve.without_moment, None
        freshest = max(active, key=lambda m: m.detected_at)
        lifetime = max((freshest.expires_at - freshest.detected_at).total_seconds(), 1.0)
        f = max(0.0, (ctx.now - freshest.detected_at).total_seconds()) / lifetime
        if f <= curve.full_until:
            return 1.0, freshest
        slope = (1.0 - curve.floor) / (1.0 - curve.full_until)
        return max(curve.floor, 1.0 - slope * (f - curve.full_until)), freshest

    def _safety(self, s: FinancialSnapshot) -> float:
        p = self.rules.financial_fit
        spending = max(s.avg_monthly_spending, p.spending_floor)
        return _clamp(
            p.projected_weight * _clamp(s.projected_balance_before_next_income / spending)
            + p.buffer_weight * _clamp(s.emergency_buffer_months / p.buffer_target_months)
        )

    def _first_suppression(self, d: _Draft, ctx: _Ctx) -> tuple[str, str] | None:
        for rule in self.rules.suppression_rules:
            if not rule.enabled:
                continue
            reason = SUPPRESSION_FUNCTIONS[rule.id](d, ctx, rule.params)
            if reason:
                return rule.id, reason
        return None

    def _candidate(self, d: _Draft, ctx: _Ctx) -> JourneyCandidate:
        return JourneyCandidate(
            journey=d.journey.type,
            driven_by=[i.type for i, _ in d.driven_by],
            score=d.breakdown.total,
            breakdown=d.breakdown,
            decision_type=self._decision_type(d.journey, d.breakdown.total, ctx.owned),
            evidence=d.evidence,
        )

    def _decision_type(self, journey: JourneyDef, score: float, owned: set[ProductType]) -> DecisionType:
        t = self.rules.thresholds
        if score < t.suggestion:
            return self.rules.passive_decision_type
        rule = self.rules.decision_types[journey.kind]
        if journey.urgent and rule.urgent:
            return rule.urgent
        covered, total = product_coverage(journey, owned)
        if total and covered == total:
            return self.rules.all_covered_decision_type
        return rule.default

    def _level(self, score: float) -> DecisionLevel:
        t = self.rules.thresholds
        if score >= t.proactive:
            return DecisionLevel.PROACTIVE
        if score >= t.suggestion:
            return DecisionLevel.SUGGESTION
        if score >= t.passive:
            return DecisionLevel.PASSIVE
        return DecisionLevel.NONE

    def _choose(
        self,
        considered: list[JourneyCandidate],
        suppressed: list[SuppressedCandidate],
        moments: Sequence[ActiveMoment],
        now: datetime,
    ) -> Decision:
        t = self.rules.thresholds
        suppressed_reasons = [
            REASONS["suppressed"].format(journey=s.journey.value, rule=s.rule, reason=s.reason)
            for s in suppressed
            if s.rule != "LOW_CONFIDENCE"
        ]
        best = considered[0] if considered else None

        if best is None or best.score < t.passive:
            emerging = [m.type.value for m in moments if m.status == MomentStatus.EMERGING]
            timing_low = best is not None and best.breakdown.timing_relevance < t.wait_timing_below
            if emerging:
                reasons = [REASONS["wait"].format(moments=", ".join(emerging))]
            elif timing_low:
                reasons = [REASONS["wait_timing"].format(journey=best.journey.value)]
            else:
                reasons = [REASONS["no_action"].format(threshold=t.passive)]
            return Decision(
                decision_type=DecisionType.WAIT if emerging or timing_low else DecisionType.NO_ACTION,
                level=DecisionLevel.NONE,
                primary=None,
                secondary=[],
                considered=considered,
                suppressed=suppressed,
                reasons=reasons + suppressed_reasons,
                decided_at=now,
            )

        level = self._level(best.score)
        secondary = [c for c in considered[1:] if c.score >= t.secondary_min_score][: t.max_secondary]
        reasons = [
            REASONS["primary"].format(journey=best.journey.value, score=best.score, level=level.value),
            REASONS["driven_by"].format(intent=best.driven_by[0].value, confidence=best.breakdown.intent_confidence),
        ]
        reasons += [REASONS["secondary"].format(journey=c.journey.value, score=c.score) for c in secondary]
        return Decision(
            decision_type=best.decision_type,
            level=level,
            primary=best,
            secondary=secondary,
            considered=considered,
            suppressed=suppressed,
            reasons=reasons + suppressed_reasons,
            decided_at=now,
        )

