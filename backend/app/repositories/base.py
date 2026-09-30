"""Repository protocols: storage behind interfaces so it can be swapped. Owner: T0.

Everything is keyed by customer id (customer isolation, A.10).
"""

from __future__ import annotations

from typing import Protocol

from app.models.customer import Customer
from app.models.event import CustomerEvent


class EventLimitExceeded(Exception):
    """The per-customer event log is full (memory abuse guard)."""


class CustomerRepository(Protocol):
    def get(self, customer_id: str) -> Customer | None: ...

    def list(self) -> list[Customer]: ...

    def update_consent(self, customer_id: str, personalization: bool) -> Customer | None: ...

    def reset(self, customer_id: str | None = None) -> None:
        """Restore seed state for one customer, or all when `customer_id` is None."""
        ...


class EventRepository(Protocol):
    def list_for(self, customer_id: str) -> list[CustomerEvent]: ...

    def append(self, event: CustomerEvent) -> CustomerEvent:
        """Store an event. Raises EventLimitExceeded when the customer's log is full."""
        ...

    def reset(self, customer_id: str | None = None) -> None: ...
