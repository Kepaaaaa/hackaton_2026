"""Pipeline orchestration: `run_pipeline` (A.8).

Owner: T0 skeleton (run_pipeline, Engines). T5 adds the PersonalizationService class.

`PersonalizationService` is the stateful shell around the pure pipeline: it reads a
customer's event log from the repositories, recomputes on read (cached per customer,
invalidated on every write) and is the only place that assigns event ids and timestamps.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from app.engines.context_engine import ContextEngine
from app.engines.decision_engine import DecisionEngine
from app.engines.experience_builder import ExperienceBuilder
from app.engines.financial_snapshot import compute_snapshot
from app.engines.intent_engine import IntentEngine
from app.engines.signal_engine import SignalEngine
from app.core.clock import Clock
from app.core.errors import NotFoundError
from app.models.common import DecisionLevel, DecisionType, FeedbackType, JourneyType
from app.models.context import CustomerContext
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.event import CustomerEvent, EventInput, FeedbackData, RecommendationFeedbackInput
from app.models.pipeline import PipelineResult
from app.models.snapshot import FinancialSnapshot
from app.repositories.base import CustomerRepository, EventRepository
from app.repositories.memory import InMemoryCustomerRepository, InMemoryEventRepository
from app.repositories.seed_loader import Scenario, load_seed

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
        experience = engines.experience.build(customer, context, [], decision, now, events=events)
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
    experience = engines.experience.build(customer, context, intents, decision, now, events=events)
    return PipelineResult(customer=customer, context=context, intents=intents, decision=decision, experience=experience)


class PersonalizationService:
    """Customer state = run_pipeline(profile, event log, now). Thread-safe, per-customer cache."""

    def __init__(
        self,
        customer_repo: CustomerRepository,
        event_repo: EventRepository,
        clock: Clock,
        engines: Engines = DEFAULT_ENGINES,
        scenarios: Sequence[Scenario] = (),
    ) -> None:
        self._customers = customer_repo
        self._events = event_repo
        self._clock = clock
        self._engines = engines
        self._lock = threading.RLock()
        self._cache: dict[str, PipelineResult] = {}
        self._scenarios = {s.id: s for s in scenarios}

    @classmethod
    def from_seed(
        cls, clock: Clock, engines: Engines = DEFAULT_ENGINES, max_events_per_customer: int = 2000
    ) -> PersonalizationService:
        """Wire in-memory repositories from the seed files, resolved against `clock.now()`."""
        seed = load_seed(clock.now())
        return cls(
            InMemoryCustomerRepository(seed.customers),
            InMemoryEventRepository(seed.events_by_customer, max_events_per_customer),
            clock,
            engines,
            seed.scenarios,
        )

    # --- reads -------------------------------------------------------------------

    def get_customer(self, customer_id: str) -> Customer:
        customer = self._customers.get(customer_id)
        if customer is None:
            raise NotFoundError()
        return customer

    def list_customers(self) -> list[Customer]:
        return self._customers.list()

    def list_events(self, customer_id: str) -> list[CustomerEvent]:
        self.get_customer(customer_id)
        return self._events.list_for(customer_id)

    def list_scenarios(self) -> list[Scenario]:
        return list(self._scenarios.values())

    def now(self) -> datetime:
        return self._clock.now()

    def get_state(self, customer_id: str) -> PipelineResult:
        with self._lock:
            cached = self._cache.get(customer_id)
            if cached is not None:
                return cached
            customer = self.get_customer(customer_id)
            result = run_pipeline(customer, self._events.list_for(customer_id), self._clock.now(), self._engines)
            self._cache[customer_id] = result
            return result

    # --- writes (each one invalidates the customer's cache) -------------------------

    def add_event(self, customer_id: str, event_input: EventInput) -> PipelineResult:
        return self.add_events(customer_id, [event_input])

    def add_events(self, customer_id: str, event_inputs: Sequence[EventInput]) -> PipelineResult:
        """Save with server-set id/timestamp/origin, then recompute. Inputs are already validated."""
        with self._lock:
            self.get_customer(customer_id)
            now = self._clock.now()
            try:
                for event_input in event_inputs:
                    event_id = self._next_event_id(customer_id)
                    self._events.append(event_input.to_event(customer_id, now, event_id))
            finally:
                self._cache.pop(customer_id, None)
            return self.get_state(customer_id)

    def add_feedback(self, customer_id: str, journey: JourneyType, feedback: FeedbackType) -> PipelineResult:
        event_input = RecommendationFeedbackInput(data=FeedbackData(journey=journey, feedback=feedback))
        return self.add_event(customer_id, event_input)

    def set_consent(self, customer_id: str, personalization: bool) -> PipelineResult:
        with self._lock:
            if self._customers.update_consent(customer_id, personalization) is None:
                raise NotFoundError()
            self._cache.pop(customer_id, None)
            return self.get_state(customer_id)

    def reset(self, customer_id: str) -> PipelineResult:
        with self._lock:
            self.get_customer(customer_id)
            self._customers.reset(customer_id)
            self._events.reset(customer_id)
            self._cache.pop(customer_id, None)
            return self.get_state(customer_id)

    def apply_scenario_step(self, customer_id: str, scenario_id: str, step_index: int) -> PipelineResult:
        """`step_index` is 0-based. The scenario must target this customer or be customer-agnostic."""
        scenario = self.scenario_for(customer_id, scenario_id)
        if not 0 <= step_index < len(scenario.steps):
            raise NotFoundError("Scenario step not found.")
        return self.add_events(customer_id, scenario.steps[step_index].events)

    def scenario_for(self, customer_id: str, scenario_id: str) -> Scenario:
        self.get_customer(customer_id)
        scenario = self._scenarios.get(scenario_id)
        if scenario is None or scenario.customer_id not in (None, customer_id):
            raise NotFoundError("Scenario not found for this customer.")
        return scenario

    def _next_event_id(self, customer_id: str) -> str:
        live = sum(1 for e in self._events.list_for(customer_id) if e.origin == "live")
        return f"evt_{customer_id}_live_{live + 1:04d}"
