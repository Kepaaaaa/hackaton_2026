"""Decision Engine: intents x journeys -> scored, suppressed, ranked decision. Owner: T4. Stub created by T0."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from app.models.common import JourneyType
from app.models.context import ActiveMoment
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.event import CustomerEvent
from app.models.intent import Intent
from app.models.journey import JourneyDef
from app.models.snapshot import FinancialSnapshot


class DecisionEngine:
    def __init__(self, rules: Any = None, journeys: Mapping[JourneyType, JourneyDef] | None = None) -> None:
        self.rules = rules
        self.journeys = journeys

    def decide(
        self,
        customer: Customer,
        snapshot: FinancialSnapshot,
        moments: Sequence[ActiveMoment],
        intents: Sequence[Intent],
        events: Sequence[CustomerEvent],
        now: datetime,
    ) -> Decision:
        raise NotImplementedError("T4")
