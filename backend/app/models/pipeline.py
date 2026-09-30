"""Full pipeline result (A.7). Owner: T0."""

from __future__ import annotations

from app.models.common import StrictModel
from app.models.context import CustomerContext
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.experience import PersonalizedExperience
from app.models.intent import Intent


class PipelineResult(StrictModel):
    customer: Customer
    context: CustomerContext
    intents: list[Intent]
    decision: Decision
    experience: PersonalizedExperience
