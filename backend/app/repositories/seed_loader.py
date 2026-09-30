"""Seed loader: `load_seed(now) -> SeedData(customers, events_by_customer, scenarios)`.

Also exports `scenario_step_events(scenario_id, step_index) -> list[EventInput]`.
Reads fixed files inside the package (no user-supplied paths), validates with the A.7 models.

Owner: T1. Stub created by T0.
"""

from __future__ import annotations

from datetime import datetime


def load_seed(now: datetime):
    raise NotImplementedError("T1")
