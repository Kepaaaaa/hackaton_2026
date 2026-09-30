"""Thread-safe in-memory repositories seeded from constructor input. Owner: T0.

Reads return deep copies so callers can never mutate stored state.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Mapping

from app.models.customer import Consent, Customer
from app.models.event import CustomerEvent
from app.repositories.base import EventLimitExceeded

DEFAULT_MAX_EVENTS_PER_CUSTOMER = 2000


class InMemoryCustomerRepository:
    def __init__(self, customers: Iterable[Customer]) -> None:
        self._lock = threading.Lock()
        self._seed: dict[str, Customer] = {c.id: c.model_copy(deep=True) for c in customers}
        self._data: dict[str, Customer] = {k: v.model_copy(deep=True) for k, v in self._seed.items()}

    def get(self, customer_id: str) -> Customer | None:
        with self._lock:
            customer = self._data.get(customer_id)
            return customer.model_copy(deep=True) if customer else None

    def list(self) -> list[Customer]:
        with self._lock:
            return [c.model_copy(deep=True) for c in self._data.values()]

    def update_consent(self, customer_id: str, personalization: bool) -> Customer | None:
        with self._lock:
            customer = self._data.get(customer_id)
            if customer is None:
                return None
            updated = customer.model_copy(update={"consent": Consent(personalization=personalization)}, deep=True)
            self._data[customer_id] = updated
            return updated.model_copy(deep=True)

    def reset(self, customer_id: str | None = None) -> None:
        with self._lock:
            if customer_id is None:
                self._data = {k: v.model_copy(deep=True) for k, v in self._seed.items()}
            elif customer_id in self._seed:
                self._data[customer_id] = self._seed[customer_id].model_copy(deep=True)


class InMemoryEventRepository:
    def __init__(
        self,
        events_by_customer: Mapping[str, Iterable[CustomerEvent]],
        max_events_per_customer: int = DEFAULT_MAX_EVENTS_PER_CUSTOMER,
    ) -> None:
        self._lock = threading.Lock()
        self._max = max_events_per_customer
        self._seed: dict[str, list[CustomerEvent]] = {
            cid: [e.model_copy(deep=True) for e in events] for cid, events in events_by_customer.items()
        }
        self._data: dict[str, list[CustomerEvent]] = self._copy_seed()

    def _copy_seed(self) -> dict[str, list[CustomerEvent]]:
        return {cid: [e.model_copy(deep=True) for e in events] for cid, events in self._seed.items()}

    def list_for(self, customer_id: str) -> list[CustomerEvent]:
        with self._lock:
            return [e.model_copy(deep=True) for e in self._data.get(customer_id, [])]

    def append(self, event: CustomerEvent) -> CustomerEvent:
        with self._lock:
            log = self._data.setdefault(event.customer_id, [])
            if len(log) >= self._max:
                raise EventLimitExceeded(f"event log limit of {self._max} reached")
            log.append(event.model_copy(deep=True))
            return event.model_copy(deep=True)

    def reset(self, customer_id: str | None = None) -> None:
        with self._lock:
            if customer_id is None:
                self._data = self._copy_seed()
            else:
                self._data[customer_id] = [e.model_copy(deep=True) for e in self._seed.get(customer_id, [])]
