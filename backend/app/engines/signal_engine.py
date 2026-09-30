"""Signal Engine: events + history -> signals with evidence. Owner: T2. Stub created by T0."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from app.models.common import SignalType
from app.models.customer import Customer
from app.models.event import CustomerEvent
from app.models.signal import Signal
from app.models.snapshot import FinancialSnapshot
from app.rules import signals as signal_rules
from app.rules.schema import PatternThresholds, SignalEventRule


class SignalEngine:
    def __init__(
        self,
        rules: Sequence[SignalEventRule] | None = None,
        thresholds: PatternThresholds | None = None,
        ttl_days: Mapping[SignalType, int] | None = None,
    ) -> None:
        self.rules = list(rules) if rules is not None else signal_rules.EVENT_SIGNAL_RULES
        self.thresholds = thresholds or signal_rules.PATTERN_THRESHOLDS
        self.ttl_days = dict(ttl_days) if ttl_days is not None else signal_rules.SIGNAL_TTL_DAYS

    def extract(self, event: CustomerEvent, now: datetime) -> list[Signal]:
        raise NotImplementedError("T2")

    def detect_patterns(
        self, customer: Customer, events: Sequence[CustomerEvent], snapshot: FinancialSnapshot, now: datetime
    ) -> list[Signal]:
        raise NotImplementedError("T2")

    def extract_all(
        self, customer: Customer, events: Sequence[CustomerEvent], snapshot: FinancialSnapshot, now: datetime
    ) -> list[Signal]:
        raise NotImplementedError("T2")
