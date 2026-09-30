"""Active moments and the customer context (A.7). Owner: T0."""

from __future__ import annotations

from pydantic import AwareDatetime

from app.models.common import Evidence, MomentStatus, MomentType, ProductType, StrictModel
from app.models.customer import CustomerProfile
from app.models.signal import Signal
from app.models.snapshot import FinancialSnapshot


class ActiveMoment(StrictModel):
    type: MomentType
    confidence: float
    status: MomentStatus
    detected_at: AwareDatetime
    expires_at: AwareDatetime
    evidence: list[Evidence]


class CustomerContext(StrictModel):
    persistent: CustomerProfile
    products: list[ProductType]
    snapshot: FinancialSnapshot
    signals: list[Signal]
    moments: list[ActiveMoment]
