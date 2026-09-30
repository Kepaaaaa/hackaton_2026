"""Pipeline orchestration: `run_pipeline` (A.8).

Owner: T0 skeleton (run_pipeline, Engines). T5 adds the PersonalizationService class.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from app.engines.context_engine import ContextEngine
from app.engines.decision_engine import DecisionEngine
from app.engines.experience_builder import ExperienceBuilder
from app.engines.financial_snapshot import compute_snapshot
from app.engines.intent_engine import IntentEngine
from app.engines.signal_engine import SignalEngine
from app.models.common import DecisionLevel, DecisionType
from app.models.context import CustomerContext
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.event import CustomerEvent
from app.models.pipeline import PipelineResult
from app.models.snapshot import FinancialSnapshot

NO_CONSENT_REASON = "NO_CONSENT: personalization is turned off by the customer."

SnapshotFn = Callable[[Customer, Sequence[CustomerEvent], datetime], FinancialSnapshot]


@dataclass(frozen=True)
class Engines:
    snapshot: SnapshotFn = compute_snapshot
    signal: SignalEngine = field(default_factory=SignalEngine)
    context: ContextEngine = field(default_factory=ContextEngine)
    intent: IntentEngine = field(default_factory=IntentEngine)
    decision: DecisionEngine = field(default_factory=DecisionEngine)
    experience: ExperienceBuilder = field(default_factory=ExperienceBuilder)


DEFAULT_ENGINES = Engines()


def run_pipeline(
    customer: Customer,
    events: Sequence[CustomerEvent],
    now: datetime,
    engines: Engines = DEFAULT_ENGINES,
) -> PipelineResult:
    """Pure function of profile + events + now. Recomputed on every read."""
    events = [e for e in events if e.customer_id == customer.id]  # customer isolation
    snapshot = engines.snapshot(customer, events, now)

    if not customer.consent.personalization:
        context = CustomerContext(
            persistent=customer.profile,
            products=customer.owned_products(),
            snapshot=snapshot,
            signals=[],
            moments=[],
        )
        decision = Decision(
            decision_type=DecisionType.NO_ACTION,
            level=DecisionLevel.NONE,
            primary=None,
            secondary=[],
            considered=[],
            suppressed=[],
            reasons=[NO_CONSENT_REASON],
            decided_at=now,
        )
        experience = engines.experience.build(customer, context, [], decision, now)
        return PipelineResult(customer=customer, context=context, intents=[], decision=decision, experience=experience)

    signals = engines.signal.extract_all(customer, events, snapshot, now)
    moments = engines.context.compute(customer, signals, now)
    intents = engines.intent.compute(customer, moments, signals, now)
    decision = engines.decision.decide(customer, snapshot, moments, intents, events, now)
    context = CustomerContext(
        persistent=customer.profile,
        products=customer.owned_products(),
        snapshot=snapshot,
        signals=signals,
        moments=moments,
    )
    experience = engines.experience.build(customer, context, intents, decision, now)
    return PipelineResult(customer=customer, context=context, intents=intents, decision=decision, experience=experience)
