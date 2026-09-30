"""Intent Engine: moments + signals + profile -> several intents. Owner: T3. Stub created by T0."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.models.context import ActiveMoment
from app.models.customer import Customer
from app.models.intent import Intent
from app.models.signal import Signal
from app.rules import intents as intent_rules
from app.rules.schema import IntentRule


class IntentEngine:
    def __init__(self, rules: Sequence[IntentRule] | None = None) -> None:
        self.rules = list(rules) if rules is not None else intent_rules.INTENT_RULES

    def compute(
        self, customer: Customer, moments: Sequence[ActiveMoment], signals: Sequence[Signal], now: datetime
    ) -> list[Intent]:
        raise NotImplementedError("T3")
