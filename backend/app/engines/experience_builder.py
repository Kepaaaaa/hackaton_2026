"""Experience Builder: decision -> structured PersonalizedExperience JSON (never HTML).

Owner: T4. Stub created by T0.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from app.models.common import JourneyType
from app.models.context import CustomerContext
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.experience import PersonalizedExperience
from app.models.intent import Intent
from app.models.journey import JourneyDef


class ExperienceBuilder:
    def __init__(self, journeys: Mapping[JourneyType, JourneyDef] | None = None, copy: Any = None) -> None:
        self.journeys = journeys
        self.copy = copy

    def build(
        self,
        customer: Customer,
        context: CustomerContext,
        intents: Sequence[Intent],
        decision: Decision,
        now: datetime,
    ) -> PersonalizedExperience:
        raise NotImplementedError("T4")
