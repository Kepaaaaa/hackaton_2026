"""compute_snapshot(customer, events, now) -> FinancialSnapshot (A.9). Owner: T2. Stub created by T0."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.models.customer import Customer
from app.models.event import CustomerEvent
from app.models.snapshot import FinancialSnapshot


def compute_snapshot(customer: Customer, events: Sequence[CustomerEvent], now: datetime) -> FinancialSnapshot:
    raise NotImplementedError("T2")
