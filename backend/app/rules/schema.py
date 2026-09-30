"""Pydantic types of rule definitions. Owner: T0.

Rules are declarative data; engines are generic loops over them. Rule values
live in the sibling modules (signals.py, moments.py, intents.py, decisions.py,
journeys.py, copy.py).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.common import EventType, IntentType, MomentType, ProductType, SignalType


class RuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


Scalar = str | float | int | bool

# --- Signals (T2) ----------------------------------------------------------------


class DataMatch(RuleModel):
    """Generic predicate on one field of an event's `data`."""

    field: str
    op: Literal["eq", "in", "ge", "gt", "le", "lt"] = "eq"
    value: Scalar | list[str]

    @model_validator(mode="after")
    def _check_value(self) -> DataMatch:
        if self.op == "in" and not isinstance(self.value, list):
            raise ValueError("op 'in' requires a list value")
        if self.op != "in" and isinstance(self.value, list):
            raise ValueError(f"op {self.op!r} requires a scalar value")
        return self


class SignalEventRule(RuleModel):
    """One event -> at most one signal, if every `match` holds."""

    event_type: EventType
    match: list[DataMatch] = []
    # KBC_SEARCH only: the lower-cased query must contain at least one keyword of EVERY group.
    keyword_groups: list[list[str]] = []
    signal: SignalType
    strength: float = Field(ge=0, le=1)
    ttl_days: int | None = Field(None, ge=1, le=730)  # None -> SIGNAL_TTL_DAYS default
    description: str | None = None  # optional template, formatted by the signal engine


class PatternThresholds(RuleModel):
    """Thresholds of the history/snapshot pattern detectors (A.9). Defaults = A.9 values."""

    first_salary_recent_days: int = 30
    first_salary_lookback_days: int = 180
    salary_stopped_history_min_days: int = 60
    salary_stopped_history_max_days: int = 180
    salary_stopped_quiet_days: int = 45
    pension_recent_days: int = 45
    pension_no_prior_before_days: int = 90
    child_expense_categories: list[str] = ["baby_supplies", "childcare"]
    child_expense_min_count: int = 3
    child_expense_window_days: int = 60
    child_expense_strength: float = 0.8
    mortgage_simulation_min_count: int = 3
    mortgage_simulation_window_days: int = 30
    low_projected_balance_abs: float = 500.0
    low_projected_balance_ratio: float = 0.3
    low_emergency_buffer_months: float = 3.0
    high_idle_cash_min: float = 10_000.0
    high_idle_ratio_min: float = 0.5


# --- Moments (T3) ----------------------------------------------------------------


class MomentRule(RuleModel):
    moment: MomentType
    signal_weights: dict[SignalType, float]
    ttl_days: int = Field(ge=1, le=730)
    requires_any: list[SignalType] = []
    cap_without_required: float = Field(1.0, ge=0, le=1)
    decay: Literal["none", "linear"] = "none"


# --- Intents (T3) ----------------------------------------------------------------


class ProfileAdjustment(RuleModel):
    """(path, equals, delta): if `CustomerProfile.<path> == equals`, add `delta`.

    Paths starting with `age` are forbidden (age is never a rule input).
    """

    path: str = Field(pattern=r"^[a-z_]+(\.[a-z_]+)*$")
    equals: Scalar
    delta: float = Field(ge=-1, le=1)

    @field_validator("path")
    @classmethod
    def _no_age(cls, v: str) -> str:
        if v.split(".")[0].startswith("age"):
            raise ValueError("age must never be used as a rule input")
        return v


class IntentRule(RuleModel):
    intent: IntentType
    moment_weights: dict[MomentType, float] = {}
    signal_weights: dict[SignalType, float] = {}
    profile_adjustments: list[ProfileAdjustment] = []


# --- Decisions (T4) ----------------------------------------------------------------


class Condition(RuleModel):
    """Eligibility condition.

    Comparison ops read `field` from a flat mapping (e.g. `snapshot.model_dump()`).
    `owns` / `not_owns` check `value` (a ProductType) against the owned products.
    """

    field: str = ""
    op: Literal["gt", "ge", "lt", "le", "eq", "owns", "not_owns"]
    value: Scalar

    @model_validator(mode="after")
    def _check(self) -> Condition:
        if self.op in ("owns", "not_owns"):
            ProductType(self.value)  # raises ValueError if unknown
        elif not self.field:
            raise ValueError(f"op {self.op!r} requires a field")
        return self

    def evaluate(self, values: Mapping[str, Any], owned: Collection[str]) -> bool:
        if self.op == "owns":
            return self.value in owned
        if self.op == "not_owns":
            return self.value not in owned
        actual = values.get(self.field)
        if actual is None:
            return False
        match self.op:
            case "gt":
                return actual > self.value
            case "ge":
                return actual >= self.value
            case "lt":
                return actual < self.value
            case "le":
                return actual <= self.value
            case _:
                return actual == self.value


class SuppressionRule(RuleModel):
    """One entry of the ordered suppression list; `id` maps to a registered function."""

    id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    description: str
    params: dict[str, Scalar | list[str]] = {}
    enabled: bool = True


class DecisionWeights(RuleModel):
    intent_confidence: float = 0.35
    timing_relevance: float = 0.25
    usefulness: float = 0.20
    eligibility: float = 0.10
    financial_fit: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


class DecisionThresholds(RuleModel):
    proactive: float = 0.80
    suggestion: float = 0.60
    passive: float = 0.40
    low_confidence: float = 0.40
    secondary_min_score: float = 0.40
    max_secondary: int = 2
    wait_timing_below: float = 0.40
