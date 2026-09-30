"""Customer read endpoints and the shared `my-kbc` payload. Owner: T5."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter

from app.api.deps import CustomerIdDep, ServiceDep
from app.models.common import StrictModel, TransactionCategory
from app.models.context import ActiveMoment, CustomerContext
from app.models.customer import Account, Customer, CustomerProfile
from app.models.decision import Decision
from app.models.event import TransactionEvent
from app.models.experience import PersonalizedExperience
from app.models.intent import Intent
from app.models.pipeline import PipelineResult
from app.models.snapshot import FinancialSnapshot

router = APIRouter(prefix="/customers", tags=["customers"])

RECENT_TRANSACTIONS = 10

_LIFE_STAGE_LABELS = {
    "student": "Student",
    "young_professional": "Young professional",
    "established": "Established professional",
    "family": "Family",
    "pre_retirement": "Pre-retirement",
    "retired": "Retired",
}
_HOUSING_LABELS = {"tenant": "tenant", "homeowner": "homeowner", "living_with_parents": "living with parents"}

# The generic view is the same for everyone: that is the point of the comparison.
GENERIC_BANNERS = [
    {"id": "BORROW_FOR_PROJECTS", "title": "Borrow for your projects", "subtitle": "Loans for every plan."},
    {"id": "INSURE_YOUR_HOME", "title": "Insure your home", "subtitle": "Home insurance from KBC."},
]


class CustomerSummary(StrictModel):
    id: str
    first_name: str
    age: int
    headline: str


class RecentTransaction(StrictModel):
    id: str
    timestamp: datetime
    direction: Literal["in", "out"]
    amount: float
    category: TransactionCategory
    merchant: str


class Banner(StrictModel):
    id: str
    title: str
    subtitle: str


class Overview(StrictModel):
    customer_id: str
    first_name: str
    accounts: list[Account]
    recent_transactions: list[RecentTransaction]
    banners: list[Banner]


class MyKbc(StrictModel):
    """Everything the frontend needs for one customer in one call."""

    customer: Customer
    profile: CustomerProfile
    snapshot: FinancialSnapshot
    moments: list[ActiveMoment]
    intents: list[Intent]
    decision: Decision
    experience: PersonalizedExperience


def headline(customer: Customer) -> str:
    p = customer.profile
    return f"{_LIFE_STAGE_LABELS[p.life_stage]}, {_HOUSING_LABELS[p.housing.status]}"


def to_my_kbc(result: PipelineResult) -> MyKbc:
    return MyKbc(
        customer=result.customer,
        profile=result.customer.profile,
        snapshot=result.context.snapshot,
        moments=result.context.moments,
        intents=result.intents,
        decision=result.decision,
        experience=result.experience,
    )


@router.get("", response_model=list[CustomerSummary], summary="List demo customers")
def list_customers(service: ServiceDep) -> list[CustomerSummary]:
    return [
        CustomerSummary(id=c.id, first_name=c.first_name, age=c.age, headline=headline(c))
        for c in service.list_customers()
    ]


@router.get("/{customer_id}", response_model=Customer, summary="Customer profile, accounts and products")
def get_customer(customer_id: CustomerIdDep, service: ServiceDep) -> Customer:
    return service.get_state(customer_id).customer


@router.get(
    "/{customer_id}/overview",
    response_model=Overview,
    summary="Generic, non-personalised view",
    description="What every customer sees today: accounts, last 10 transactions and the same static banners.",
)
def get_overview(customer_id: CustomerIdDep, service: ServiceDep) -> Overview:
    result = service.get_state(customer_id)
    customer, snapshot = result.customer, result.context.snapshot
    current_accounts = [a for a in customer.accounts if a.type == "current"]
    accounts = [
        a.model_copy(update={"balance": snapshot.current_balance})
        if len(current_accounts) == 1 and a.type == "current"
        else a
        for a in customer.accounts
    ]
    now = service.now()
    txs = sorted(
        (e for e in service.list_events(customer_id) if isinstance(e, TransactionEvent) and e.timestamp <= now),
        key=lambda e: e.timestamp,
        reverse=True,
    )[:RECENT_TRANSACTIONS]
    return Overview(
        customer_id=customer.id,
        first_name=customer.first_name,
        accounts=accounts,
        recent_transactions=[
            RecentTransaction(
                id=e.id,
                timestamp=e.timestamp,
                direction=e.data.direction,
                amount=e.data.amount,
                category=e.data.category,
                merchant=e.data.merchant,
            )
            for e in txs
        ],
        banners=[Banner(**b) for b in GENERIC_BANNERS],
    )


@router.get("/{customer_id}/context", response_model=CustomerContext, summary="Snapshot, signals and active moments")
def get_context(customer_id: CustomerIdDep, service: ServiceDep) -> CustomerContext:
    return service.get_state(customer_id).context


@router.get("/{customer_id}/intents", response_model=list[Intent], summary="Probable needs, with confidence")
def get_intents(customer_id: CustomerIdDep, service: ServiceDep) -> list[Intent]:
    return service.get_state(customer_id).intents


@router.get("/{customer_id}/decision", response_model=Decision, summary="What KBC should do now (maybe nothing)")
def get_decision(customer_id: CustomerIdDep, service: ServiceDep) -> Decision:
    return service.get_state(customer_id).decision


@router.get(
    "/{customer_id}/experience", response_model=PersonalizedExperience, summary="Structured experience JSON"
)
def get_experience(customer_id: CustomerIdDep, service: ServiceDep) -> PersonalizedExperience:
    return service.get_state(customer_id).experience


@router.get("/{customer_id}/my-kbc", response_model=MyKbc, summary="Everything the frontend needs")
def get_my_kbc(customer_id: CustomerIdDep, service: ServiceDep) -> MyKbc:
    return to_my_kbc(service.get_state(customer_id))
