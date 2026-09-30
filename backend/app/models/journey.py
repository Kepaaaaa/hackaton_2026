"""Journey definitions (A.7). Definitions live in rules/journeys.py, instances in the experience. Owner: T0."""

from __future__ import annotations

from app.models.common import ActionKind, IntentType, JourneyKind, JourneyType, ProductType, StrictModel
from app.rules.schema import Condition


class JourneyActionDef(StrictModel):
    id: str
    kind: ActionKind
    label: str
    product: ProductType | None = None  # if set and owned -> ALREADY_COVERED
    calculator: str | None = None  # name of a calculators.py function feeding payload
    # Addition to A.7: static calculator inputs / demo assumptions (e.g. {"target": 100000, "horizon_years": 40}).
    params: dict[str, float | int | str | bool] = {}


class JourneyDef(StrictModel):
    type: JourneyType
    title: str
    kind: JourneyKind
    serves_intents: dict[IntentType, float]  # relevance of this journey for each intent (0..1)
    usefulness: float  # base usefulness 0..1
    urgent: bool = False  # SUPPORT journeys may be urgent
    eligibility: list[Condition] = []
    actions: list[JourneyActionDef]
