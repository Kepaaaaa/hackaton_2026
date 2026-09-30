"""Tests for scoring and context_engine. Owner: T3."""

from __future__ import annotations

import inspect
from datetime import timedelta

import pytest
from conftest import NOW, make_customer, make_signal

from app.engines import context_engine, scoring
from app.engines.context_engine import ContextEngine
from app.engines.scoring import Contributor, weighted_sum
from app.models.common import MomentStatus, MomentType, SignalType
from app.rules.moments import MOMENT_RULES
from app.rules.schema import MomentRule

S = SignalType
CUSTOMER = make_customer()


def compute(signals, rules=None):
    return ContextEngine(rules).compute(CUSTOMER, signals, NOW)


def moment(moments, type_):
    return next((m for m in moments if m.type == type_), None)


def assert_evidence_adds_up(item):
    assert sum(e.contribution for e in item.evidence) == pytest.approx(item.confidence, abs=1e-6)


# --- scoring ----------------------------------------------------------------------------


def test_weighted_sum_basic():
    score, ev = weighted_sum([Contributor("A", "signal", 0.5, 0.8, "a"), Contributor("B", "signal", 0.2, 1.0, "b")])
    assert score == pytest.approx(0.6)
    assert [e.contribution for e in ev] == pytest.approx([0.4, 0.2])


def test_weighted_sum_cap_adds_rule_evidence():
    score, ev = weighted_sum([Contributor("A", "signal", 0.9, 1.0, "a"), Contributor("B", "signal", 0.5, 1.0, "b")])
    assert score == 1.0
    assert ev[-1].kind == "rule" and ev[-1].contribution == pytest.approx(-0.4)
    assert sum(e.contribution for e in ev) == pytest.approx(score)


def test_weighted_sum_floor():
    score, ev = weighted_sum([Contributor("A", "profile", -0.2, 1.0, "a")])
    assert score == 0.0
    assert sum(e.contribution for e in ev) == pytest.approx(0.0)


def test_weighted_sum_empty():
    assert weighted_sum([]) == (0.0, [])


# --- context engine: car sequence (electric_car scenario) ---------------------------------


@pytest.mark.parametrize(
    ("steps", "expected", "status"),
    [
        ([S.AUTOMOTIVE_TRANSACTION], 0.25, MomentStatus.EMERGING),
        ([S.AUTOMOTIVE_TRANSACTION, S.ELECTRIC_CAR_LOAN_PAGE_VIEW], 0.55, MomentStatus.ACTIVE),
        ([S.AUTOMOTIVE_TRANSACTION, S.ELECTRIC_CAR_LOAN_PAGE_VIEW, S.ELECTRIC_CAR_LOAN_SIMULATION], 0.85, MomentStatus.ACTIVE),
        (
            [S.AUTOMOTIVE_TRANSACTION, S.ELECTRIC_CAR_LOAN_PAGE_VIEW, S.ELECTRIC_CAR_LOAN_SIMULATION, S.CAR_FINANCING_KBC_SEARCH],
            1.0,
            MomentStatus.ACTIVE,
        ),
    ],
)
def test_car_sequence(steps, expected, status):
    signals = [make_signal(t, days_ago=len(steps) - i) for i, t in enumerate(steps)]
    car = moment(compute(signals), MomentType.CAR_PROJECT)
    assert car is not None
    assert car.confidence == pytest.approx(expected)
    assert car.status == status
    assert_evidence_adds_up(car)


def test_car_capped_at_one_with_extra_duplicate_signals():
    signals = [
        make_signal(t, days_ago=d)
        for d in (1, 2)
        for t in (S.AUTOMOTIVE_TRANSACTION, S.ELECTRIC_CAR_LOAN_PAGE_VIEW, S.ELECTRIC_CAR_LOAN_SIMULATION, S.CAR_FINANCING_KBC_SEARCH)
    ]
    car = moment(compute(signals), MomentType.CAR_PROJECT)
    assert car.confidence == 1.0
    # Same signal type counted once: one evidence per signal type.
    assert len([e for e in car.evidence if e.kind == "signal"]) == 4


def test_strongest_signal_per_type_is_used():
    signals = [make_signal(S.AIR_TRAVEL_ACTIVITY, strength=0.4, days_ago=2), make_signal(S.AIR_TRAVEL_ACTIVITY, strength=0.8, days_ago=5),
               make_signal(S.HOTEL_BOOKING, days_ago=1)]
    travel = moment(compute(signals), MomentType.TRAVEL)
    assert travel.confidence == pytest.approx(0.35 * 0.8 + 0.25)


# --- sensitive moments must be declared ---------------------------------------------------


def test_new_parent_capped_without_declaration():
    signals = [make_signal(S.CHILD_RELATED_EXPENSE, days_ago=d) for d in range(1, 10)]
    signals += [make_signal(S.NEW_RECURRING_CHILD_EXPENSES, strength=0.8, source="pattern"),
                make_signal(S.CHILD_SAVINGS_PAGE_VIEW, days_ago=3)]
    parent = moment(compute(signals), MomentType.NEW_PARENT)
    assert parent.confidence == pytest.approx(0.35)
    assert parent.status == MomentStatus.EMERGING
    cap = parent.evidence[-1]
    assert cap.kind == "rule" and cap.ref == "requires_any"
    assert "declared by the customer" in cap.detail
    assert_evidence_adds_up(parent)


def test_new_parent_with_declaration():
    signals = [make_signal(S.PARENTHOOD_DECLARED, days_ago=10, ttl_days=365), make_signal(S.CHILD_RELATED_EXPENSE, days_ago=3),
               make_signal(S.NEW_RECURRING_CHILD_EXPENSES, strength=0.8, source="pattern"), make_signal(S.CHILD_SAVINGS_PAGE_VIEW, days_ago=2)]
    parent = moment(compute(signals), MomentType.NEW_PARENT)
    assert parent.confidence >= 0.80
    assert parent.status == MomentStatus.ACTIVE
    assert not any(e.kind == "rule" for e in parent.evidence)


# --- TTL, timing, decay -----------------------------------------------------------------------


def test_old_airline_signal_gives_no_travel():
    # Signal itself still alive (TTL 60) but outside the TRAVEL window (30 days).
    moments = compute([make_signal(S.AIR_TRAVEL_ACTIVITY, strength=0.8, days_ago=40, ttl_days=60),
                       make_signal(S.HOTEL_BOOKING, days_ago=40, ttl_days=60)])
    assert moment(moments, MomentType.TRAVEL) is None


def test_expired_and_future_signals_ignored():
    expired = make_signal(S.AUTOMOTIVE_TRANSACTION, days_ago=10, ttl_days=5)
    future = make_signal(S.ELECTRIC_CAR_LOAN_PAGE_VIEW, days_ago=-1)
    assert compute([expired, future]) == []


def test_detected_and_expires_at():
    signals = [make_signal(S.AUTOMOTIVE_TRANSACTION, days_ago=10), make_signal(S.ELECTRIC_CAR_LOAN_PAGE_VIEW, days_ago=2)]
    car = moment(compute(signals), MomentType.CAR_PROJECT)
    assert car.detected_at == NOW - timedelta(days=10)
    assert car.expires_at == NOW - timedelta(days=2) + timedelta(days=60)


def test_linear_decay():
    rule = MomentRule(moment=MomentType.TRAVEL, signal_weights={S.HOTEL_BOOKING: 1.0}, ttl_days=30, decay="linear")
    travel = compute([make_signal(S.HOTEL_BOOKING, days_ago=15)], rules=[rule])[0]
    assert travel.confidence == pytest.approx(0.5)


def test_below_emerging_threshold_not_returned():
    # LOW_EMERGENCY_BUFFER alone: FIRST_SALARY 0.10, CASHFLOW_PRESSURE 0.10 -> nothing.
    assert compute([make_signal(S.LOW_EMERGENCY_BUFFER, source="pattern")]) == []


def test_empty_signals_no_moments():
    assert compute([]) == []


def test_sorted_by_confidence_and_all_evidence_adds_up():
    signals = [make_signal(S.FIRST_RECURRING_SALARY, source="pattern"), make_signal(S.SALARY_RECEIVED, days_ago=2),
               make_signal(S.LOW_EMERGENCY_BUFFER, source="pattern"), make_signal(S.AUTOMOTIVE_TRANSACTION)]
    moments = compute(signals)
    assert [m.type for m in moments] == [MomentType.FIRST_SALARY, MomentType.CAR_PROJECT]
    assert moments[0].confidence == pytest.approx(0.95)
    for m in moments:
        assert_evidence_adds_up(m)


def test_deterministic():
    signals = [make_signal(S.AUTOMOTIVE_TRANSACTION, source_event_ids=["e1"]), make_signal(S.ELECTRIC_CAR_LOAN_PAGE_VIEW)]
    assert compute(signals) == compute(list(reversed(signals)))
    evidence = {e.ref: e for e in compute(signals)[0].evidence}
    assert evidence[S.AUTOMOTIVE_TRANSACTION.value].source_event_ids == ["e1"]


# --- rules are data -----------------------------------------------------------------------------


def test_every_moment_has_a_rule():
    assert {r.moment for r in MOMENT_RULES} == set(MomentType)


def test_engines_contain_no_moment_or_signal_names():
    src = inspect.getsource(context_engine) + inspect.getsource(scoring)
    for name in [*MomentType, *SignalType]:
        assert name.value not in src
