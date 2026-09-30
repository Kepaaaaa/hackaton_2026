"""End-to-end persona tests: real seed data through `run_pipeline` (A.4). Owner: T6."""

from __future__ import annotations

import pytest
from conftest import NOW

from app.models.common import (
    ActionStatus,
    DecisionLevel,
    DecisionType,
    IntentType,
    JourneyType,
    MomentStatus,
    MomentType,
)
from app.models.pipeline import PipelineResult
from app.repositories.seed_loader import load_seed
from app.services.personalization_service import run_pipeline

EXPERIENCE_FIELDS = {"hero", "primary_journey", "notices", "why", "checks", "under_the_hood", "disclaimer"}


@pytest.fixture(scope="module")
def results() -> dict[str, PipelineResult]:
    seed = load_seed(NOW)
    return {c.id: run_pipeline(c, seed.events_by_customer[c.id], NOW) for c in seed.customers}


def moments(r: PipelineResult) -> dict[MomentType, float]:
    return {m.type: m.confidence for m in r.context.moments}


def active_moments(r: PipelineResult) -> set[MomentType]:
    return {m.type for m in r.context.moments if m.status == MomentStatus.ACTIVE}


def intents(r: PipelineResult) -> dict[IntentType, float]:
    return {i.type: i.confidence for i in r.intents}


def primary_actions(r: PipelineResult) -> dict[str, dict]:
    assert r.experience.primary_journey is not None
    return {a.id: a for a in r.experience.primary_journey.actions}


def test_every_persona_is_seeded(results: dict[str, PipelineResult]) -> None:
    assert set(results) == {"lucas", "julie", "marc", "claire"}


# --- Lucas: first salary ---------------------------------------------------


def test_lucas_first_salary(results: dict[str, PipelineResult]) -> None:
    r = results["lucas"]
    assert moments(r)[MomentType.FIRST_SALARY] >= 0.80
    i = intents(r)
    assert i[IntentType.BUILD_FINANCIAL_SAFETY] >= 0.85
    assert i[IntentType.START_SAVING] >= 0.70
    assert i[IntentType.START_INVESTING] <= 0.40  # visible under the hood, never acted on
    assert r.decision.decision_type == DecisionType.SHOW_JOURNEY
    assert r.decision.level == DecisionLevel.PROACTIVE
    assert r.decision.primary is not None and r.decision.primary.journey == JourneyType.FINANCIAL_FOUNDATION
    assert r.experience.mode == "PROACTIVE"


def test_lucas_pension_goal_numbers(results: dict[str, PipelineResult]) -> None:
    pension = primary_actions(results["lucas"])["LONG_TERM_PENSION_SAVINGS"]
    assert pension.status == ActionStatus.AVAILABLE
    assert pension.payload["target"] == 100_000
    assert pension.payload["monthly"] == 110
    assert pension.payload["progress_without_change"] == pytest.approx(0.06, abs=0.005)


# --- Julie: first child, declared -----------------------------------------


def test_julie_new_parent(results: dict[str, PipelineResult]) -> None:
    r = results["julie"]
    assert moments(r)[MomentType.NEW_PARENT] >= 0.80
    assert {IntentType.CHILD_SAVING, IntentType.HOUSEHOLD_BUDGET_ADAPTATION, IntentType.FAMILY_PROTECTION} <= set(intents(r))
    assert r.decision.decision_type == DecisionType.SHOW_JOURNEY
    assert r.decision.primary is not None and r.decision.primary.journey == JourneyType.FAMILY_START


def test_julie_child_savings_numbers(results: dict[str, PipelineResult]) -> None:
    child = primary_actions(results["julie"])["CHILD_LONG_TERM_SAVINGS"]
    assert child.payload["target"] == 20_000
    assert child.payload["monthly"] == 60
    assert child.payload["progress_without_change"] == pytest.approx(0.21, abs=0.005)


def test_julie_weak_first_salary_stays_emerging(results: dict[str, PipelineResult]) -> None:
    """A long-salaried customer with a low buffer gets a weak FIRST_SALARY (salary + low buffer only).
    It must stay below ACTIVE and never reach the decision."""
    r = results["julie"]
    assert MomentType.FIRST_SALARY not in active_moments(r)
    assert moments(r).get(MomentType.FIRST_SALARY, 0) < 0.40
    journeys = [c.journey for c in [r.decision.primary, *r.decision.secondary] if c]
    assert JourneyType.FINANCIAL_FOUNDATION not in journeys


# --- Marc: retirement -------------------------------------------------------


def test_marc_retirement(results: dict[str, PipelineResult]) -> None:
    r = results["marc"]
    assert moments(r)[MomentType.RETIREMENT_TRANSITION] >= 0.80
    assert {
        IntentType.INCOME_REORGANIZATION,
        IntentType.SAVINGS_MANAGEMENT,
        IntentType.LONG_TERM_FINANCIAL_PLANNING,
    } <= set(intents(r))
    assert r.decision.decision_type == DecisionType.SHOW_JOURNEY
    assert r.decision.primary is not None and r.decision.primary.journey == JourneyType.RETIREMENT_TRANSITION


def test_marc_idle_cash_and_advisor(results: dict[str, PipelineResult]) -> None:
    actions = primary_actions(results["marc"])
    idle = actions["IDLE_CASH_INSIGHT"].payload
    assert idle["idle_cash"] == pytest.approx(40_000)
    assert idle["cushion"] == pytest.approx(14_400)
    assert idle["idle_ratio"] == pytest.approx(0.74, abs=0.005)
    assert any(a.kind == "APPOINTMENT" and a.status == ActionStatus.AVAILABLE for a in actions.values())


# --- Claire: nothing to do --------------------------------------------------


def test_claire_no_action_calm(results: dict[str, PipelineResult]) -> None:
    r = results["claire"]
    assert active_moments(r) == set()
    assert all(i.confidence < 0.40 for i in r.intents)
    assert r.decision.decision_type == DecisionType.NO_ACTION
    assert r.decision.level == DecisionLevel.NONE
    assert r.decision.primary is None
    e = r.experience
    assert e.mode == "CALM"
    assert e.hero.title == "Everything looks on track."
    assert e.primary_journey is None and e.secondary_journeys == []
    assert e.checks and all(c.ok for c in e.checks)


# --- Shared experience contract ----------------------------------------------


@pytest.mark.parametrize("customer_id", ["lucas", "julie", "marc", "claire"])
def test_experience_has_every_frontend_field(results: dict[str, PipelineResult], customer_id: str) -> None:
    e = results[customer_id].experience
    assert EXPERIENCE_FIELDS <= set(type(e).model_fields)
    assert e.customer_id == customer_id
    assert e.hero.title and e.disclaimer
    assert e.checks
    assert e.under_the_hood.decision == results[customer_id].decision


@pytest.mark.parametrize("customer_id", ["lucas", "julie", "marc"])
def test_proactive_personas_explain_why(results: dict[str, PipelineResult], customer_id: str) -> None:
    r = results[customer_id]
    assert r.experience.why, "a shown journey must say why"
    assert r.decision.primary is not None and r.decision.primary.evidence
