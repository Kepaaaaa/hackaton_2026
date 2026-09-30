"""Event ingestion: post a fact, get the recomputed experience back. Owner: T5."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.customers import MyKbc, to_my_kbc
from app.api.deps import CustomerIdDep, ServiceDep
from app.models.event import EventInput

router = APIRouter(prefix="/customers", tags=["events"])


@router.post(
    "/{customer_id}/events",
    response_model=MyKbc,
    summary="Add an event and recompute",
    description=(
        "The server sets the event id, timestamp and origin (`live`). "
        "`days_ago` (0-365) is a demo-only time shift."
    ),
)
def post_event(customer_id: CustomerIdDep, event: EventInput, service: ServiceDep) -> MyKbc:
    return to_my_kbc(service.add_event(customer_id, event))
