"""Structured experience JSON rendered by the frontend (A.7). Never HTML. Owner: T0."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime

from app.models.common import ActionKind, ActionStatus, CustomerId, DecisionType, JourneyType, ProductType, StrictModel
from app.models.context import ActiveMoment
from app.models.customer import CustomerProfile
from app.models.decision import Decision
from app.models.intent import Intent
from app.models.signal import Signal
from app.models.snapshot import FinancialSnapshot


class ExperienceAction(StrictModel):
    id: str
    kind: ActionKind
    label: str
    status: ActionStatus
    payload: dict[str, float | int | str | bool] = {}


class Hero(StrictModel):
    type: str
    title: str
    subtitle: str
    tone: Literal["calm", "positive", "attention", "warning"]


class JourneyCard(StrictModel):
    type: JourneyType
    title: str
    priority: float
    decision_type: DecisionType
    actions: list[ExperienceAction]


class Notice(StrictModel):
    kind: Literal["reassurance", "warning", "info"]
    text: str


class WhyItem(StrictModel):
    text: str
    contribution: float


class CheckItem(StrictModel):
    """One line of "what we checked" (calm mode)."""

    label: str
    ok: bool
    detail: str


class UnderTheHood(StrictModel):
    persistent_context: CustomerProfile
    products: list[ProductType]
    snapshot: FinancialSnapshot
    signals: list[Signal]
    moments: list[ActiveMoment]
    intents: list[Intent]
    decision: Decision
    timing: dict[str, str]  # e.g. {"computed_at": ..., "FIRST_SALARY_expires_at": ...}


class PersonalizedExperience(StrictModel):
    customer_id: CustomerId
    mode: Literal["PROACTIVE", "SUGGESTION", "PASSIVE", "WAIT", "CALM"]
    hero: Hero
    primary_journey: JourneyCard | None
    secondary_journeys: list[JourneyCard]
    notices: list[Notice]
    why: list[WhyItem]
    checks: list[CheckItem]
    under_the_hood: UnderTheHood
    generated_at: AwareDatetime
    disclaimer: str
