"""Shared fixtures and builders. Owner: T0.

Builders are plain functions: `from conftest import make_event, NOW` in any test.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.clock import FixedClock
from app.models.common import EventType, IntentType, MomentStatus, MomentType, SignalType
from app.models.context import ActiveMoment
from app.models.customer import Customer
from app.models.event import CustomerEvent, CustomerEventAdapter
from app.models.intent import Intent
from app.models.signal import Signal
from app.models.snapshot import FinancialSnapshot

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
TEST_CUSTOMER_ID = "test_customer"

_event_ids = itertools.count(1)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(NOW)


def make_customer(**overrides: Any) -> Customer:
    """Neutral salaried tenant. Top-level keys in `overrides` replace the defaults."""
    data: dict[str, Any] = {
        "id": TEST_CUSTOMER_ID,
        "first_name": "Test",
        "age": 30,
        "profile": {
            "life_stage": "young_professional",
            "employment": {"status": "employed", "type": "salaried"},
            "income_stage": "established",
            "housing": {"status": "tenant", "mortgage": False},
            "family": {"status": "single", "children": 0},
            "financial_profile": {
                "savings_level": "medium",
                "income_stability": "stable",
                "financial_maturity": "intermediate",
            },
        },
        "accounts": [
            {"id": "acc_current", "type": "current", "label": "Current account", "masked_number": "•••• 0001", "balance": 3000.0},
            {"id": "acc_savings", "type": "savings", "label": "Savings account", "masked_number": "•••• 0002", "balance": 2000.0},
        ],
        "products": [
            {"product": "current_account", "since": "2020-01-01"},
            {"product": "savings_account", "since": "2020-01-01"},
        ],
        "consent": {"personalization": True},
    }
    data.update(overrides)
    return Customer.model_validate(data)


def make_event(
    type: EventType | str,
    data: dict[str, Any],
    days_ago: float = 0,
    origin: str = "seed",
    customer_id: str = TEST_CUSTOMER_ID,
    id: str | None = None,
    now: datetime = NOW,
) -> CustomerEvent:
    return CustomerEventAdapter.validate_python(
        {
            "id": id or f"evt_test_{next(_event_ids)}",
            "customer_id": customer_id,
            "timestamp": now - timedelta(days=days_ago),
            "origin": origin,
            "type": EventType(type),
            "data": data,
        }
    )


def make_signal(
    type: SignalType | str,
    strength: float = 1.0,
    days_ago: float = 0,
    ttl_days: int | None = 60,
    source: str = "event",
    source_event_ids: list[str] | None = None,
    now: datetime = NOW,
) -> Signal:
    ts = now - timedelta(days=days_ago)
    return Signal(
        type=SignalType(type),
        strength=strength,
        timestamp=ts,
        expires_at=ts + timedelta(days=ttl_days) if ttl_days is not None else None,
        source=source,
        source_event_ids=source_event_ids or [],
        description=f"Test signal {type}",
    )


def make_moment(
    type: MomentType | str,
    confidence: float,
    days_ago: float = 0,
    ttl_days: int = 30,
    now: datetime = NOW,
) -> ActiveMoment:
    detected = now - timedelta(days=days_ago)
    status = MomentStatus.ACTIVE if confidence >= 0.40 else MomentStatus.EMERGING
    return ActiveMoment(
        type=MomentType(type),
        confidence=confidence,
        status=status,
        detected_at=detected,
        expires_at=detected + timedelta(days=ttl_days),
        evidence=[],
    )


def make_intent(
    type: IntentType | str,
    confidence: float,
    related_moments: list[MomentType] | None = None,
) -> Intent:
    return Intent(type=IntentType(type), confidence=confidence, related_moments=related_moments or [], evidence=[])


def make_snapshot(**overrides: Any) -> FinancialSnapshot:
    """Healthy salaried default (salary 3,000, spending 2,000). Override any field."""
    data: dict[str, Any] = {
        "as_of": NOW,
        "current_balance": 3000.0,
        "savings_balance": 10000.0,
        "liquid_balance": 13000.0,
        "monthly_income": 3000.0,
        "income_sources": ["salary"],
        "avg_monthly_spending": 2000.0,
        "next_income_date": (NOW + timedelta(days=20)).date(),
        "days_until_next_income": 20,
        "projected_balance_before_next_income": 3000.0 - 2000.0 * 20 / 30,
        "emergency_buffer_months": (10000.0 + 1000.0) / 2000.0,
        "idle_cash": 1000.0,
        "idle_ratio": 1000.0 / 13000.0,
        "monthly_debt_payments": 0.0,
        "debt_ratio": 0.0,
        "monthly_margin": 1000.0,
    }
    data.update(overrides)
    return FinancialSnapshot.model_validate(data)
