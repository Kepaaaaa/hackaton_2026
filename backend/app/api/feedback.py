"""Feedback and consent: the customer stays in control. Owner: T5."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.customers import MyKbc, to_my_kbc
from app.api.deps import CustomerIdDep, ServiceDep
from app.models.common import StrictModel
from app.models.event import FeedbackData

router = APIRouter(prefix="/customers", tags=["feedback"])


class ConsentIn(StrictModel):
    personalization: bool


@router.post(
    "/{customer_id}/feedback",
    response_model=MyKbc,
    summary="Give feedback on a journey",
    description="`NOT_RELEVANT` suppresses the journey for a while, `LATER` lowers its score, `USEFUL` is recorded.",
)
def post_feedback(customer_id: CustomerIdDep, body: FeedbackData, service: ServiceDep) -> MyKbc:
    return to_my_kbc(service.add_feedback(customer_id, body.journey, body.feedback))


@router.put(
    "/{customer_id}/consent",
    response_model=MyKbc,
    summary="Turn personalization on or off",
    description="With personalization off, the decision is always `NO_ACTION` (reason `NO_CONSENT`).",
)
def put_consent(customer_id: CustomerIdDep, body: ConsentIn, service: ServiceDep) -> MyKbc:
    return to_my_kbc(service.set_consent(customer_id, body.personalization))
