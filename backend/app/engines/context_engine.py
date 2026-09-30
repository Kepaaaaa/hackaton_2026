"""Context Engine: signals -> Active Moments (confidence + TTL). Owner: T3. Stub created by T0."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.models.context import ActiveMoment
from app.models.customer import Customer
from app.models.signal import Signal
from app.rules import moments as moment_rules
from app.rules.schema import MomentRule


class ContextEngine:
    def __init__(self, rules: Sequence[MomentRule] | None = None) -> None:
        self.rules = list(rules) if rules is not None else moment_rules.MOMENT_RULES

    def compute(self, customer: Customer, signals: Sequence[Signal], now: datetime) -> list[ActiveMoment]:
        raise NotImplementedError("T3")
