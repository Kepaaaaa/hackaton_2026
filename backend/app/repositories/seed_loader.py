"""Seed loader: `load_seed(now) -> SeedData(customers, events_by_customer, scenarios)`.

Also exports `scenario_step_events(scenario_id, step_index) -> list[EventInput]`.
Reads fixed files inside the package (no user-supplied paths), validates with the A.7 models.
Seed events use relative time (`days_ago`, optional `hour`) resolved against `now`,
so the demo never goes stale. Any invalid seed file fails loudly at startup.

Owner: T1.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, StringConstraints, TypeAdapter

from app.models.common import CustomerId, EventType, StrictModel
from app.models.customer import Customer
from app.models.event import CustomerEvent, CustomerEventAdapter, EventInput

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
EVENTS_FILE = DATA_DIR / "events.json"
SCENARIOS_FILE = DATA_DIR / "scenarios.json"


class SeedEvent(StrictModel):
    """One event of `events.json`, in relative time. Payload validated by the event models."""

    days_ago: int = Field(ge=0, le=365)
    hour: int | None = Field(None, ge=0, le=23)
    type: EventType
    data: dict[str, Any]


class ScenarioStep(StrictModel):
    label: str = Field(min_length=1, max_length=120)
    events: list[EventInput] = Field(min_length=1)


class Scenario(StrictModel):
    id: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{1,39}$")]
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    customer_id: CustomerId | None = None  # None = applicable to any customer
    steps: list[ScenarioStep] = Field(min_length=1)


@dataclass(frozen=True)
class SeedData:
    customers: list[Customer]
    events_by_customer: dict[str, list[CustomerEvent]]
    scenarios: list[Scenario]


_seed_events_adapter = TypeAdapter(dict[CustomerId, list[SeedEvent]])
_customers_adapter = TypeAdapter(list[Customer])
_scenarios_adapter = TypeAdapter(list[Scenario])


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_timestamp(now: datetime, days_ago: int, hour: int | None) -> datetime:
    """`now - days_ago`, at `hour` o'clock when given; never later than `now`."""
    ts = now - timedelta(days=days_ago)
    if hour is not None:
        ts = datetime.combine(ts.date(), time(hour), tzinfo=now.tzinfo)
    return min(ts, now)


def _build_events(customer_id: str, seed_events: list[SeedEvent], now: datetime) -> list[CustomerEvent]:
    """Validate, resolve time, sort chronologically and assign deterministic ids."""
    timed = sorted(
        ((_resolve_timestamp(now, e.days_ago, e.hour), i, e) for i, e in enumerate(seed_events)),
        key=lambda t: (t[0], t[1]),
    )
    return [
        CustomerEventAdapter.validate_python(
            {
                "id": f"evt_{customer_id}_{n:04d}",
                "customer_id": customer_id,
                "timestamp": ts,
                "origin": "seed",
                "type": e.type,
                "data": e.data,
            }
        )
        for n, (ts, _, e) in enumerate(timed, start=1)
    ]


@lru_cache(maxsize=1)
def _load_scenarios() -> tuple[Scenario, ...]:
    return tuple(_scenarios_adapter.validate_python(_read_json(SCENARIOS_FILE)))


def load_seed(now: datetime) -> SeedData:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    customers = _customers_adapter.validate_python(_read_json(CUSTOMERS_FILE))
    ids = [c.id for c in customers]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate customer id in seed data")
    known = set(ids)

    raw_events = _seed_events_adapter.validate_python(_read_json(EVENTS_FILE))
    unknown = set(raw_events) - known
    if unknown:
        raise ValueError(f"events for unknown customers: {sorted(unknown)}")
    events_by_customer = {cid: _build_events(cid, raw_events.get(cid, []), now) for cid in ids}

    scenarios = [s.model_copy(deep=True) for s in _load_scenarios()]
    for s in scenarios:
        if s.customer_id is not None and s.customer_id not in known:
            raise ValueError(f"scenario {s.id} targets an unknown customer")
    if len({s.id for s in scenarios}) != len(scenarios):
        raise ValueError("duplicate scenario id in seed data")

    return SeedData(customers=customers, events_by_customer=events_by_customer, scenarios=scenarios)


def get_scenario(scenario_id: str) -> Scenario | None:
    for s in _load_scenarios():
        if s.id == scenario_id:
            return s.model_copy(deep=True)
    return None


def scenario_step_events(scenario_id: str, step_index: int) -> list[EventInput]:
    """Events of one scenario step (0-based). KeyError if unknown scenario, IndexError if bad step."""
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise KeyError(scenario_id)
    if not 0 <= step_index < len(scenario.steps):
        raise IndexError(step_index)
    return [e.model_copy(deep=True) for e in scenario.steps[step_index].events]
