"""End-to-end scenario tests: A.4 demo scenarios step by step through `run_pipeline`. Owner: T6.

Scenario events are applied as `origin="live"`, like the API does. Also covers consent,
declared-only parenthood, determinism and anti-hardcoding.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import NOW

from app.models.common import (
    ActionStatus,
    DecisionType,
    EventType,
    IntentType,
    JourneyType,
    MomentStatus,
    MomentType,
    ProductType,
)
from app.models.customer import Consent, Customer
from app.models.event import CustomerEvent
from app.models.pipeline import PipelineResult
from app.repositories.seed_loader import SeedData, load_seed, scenario_step_events
from app.services.personalization_service import run_pipeline

APP_DIR = Path(__file__).resolve().parent.parent / "app"


@pytest.fixture(scope="module")
def seed() -> SeedData:
    return load_seed(NOW)


def customer(seed: SeedData, customer_id: str) -> Customer:
    return next(c for c in seed.customers if c.id == customer_id)


def run_scenario(seed: SeedData, scenario_id: str) -> list[PipelineResult]:
    """Apply each step on top of the seed history; return the result after every step."""
    scenario = next(s for s in seed.scenarios if s.id == scenario_id)
    cust = customer(seed, scenario.customer_id)
    events: list[CustomerEvent] = list(seed.events_by_customer[cust.id])
    results = []
    for step in range(len(scenario.steps)):
        for n, event_input in enumerate(scenario_step_events(scenario_id, step)):
            events.append(event_input.to_event(cust.id, NOW, f"evt_live_{scenario_id}_{step}_{n}"))
        results.append(run_pipeline(cust, events, NOW))
    return results


def moment(r: PipelineResult, t: MomentType):
    return next((m for m in r.context.moments if m.type == t), None)


def intent_conf(r: PipelineResult, t: IntentType) -> float:
    return next((i.confidence for i in r.intents if i.type == t), 0.0)


def shown(r: PipelineResult) -> list[JourneyType]:
    return [c.journey for c in [r.decision.primary, *r.decision.secondary] if c]


def suppressed(r: PipelineResult) -> dict[JourneyType, str]:
    return {s.journey: s.rule for s in r.decision.suppressed}


def card_actions(r: PipelineResult, journey: JourneyType):
    cards = [c for c in [r.experience.primary_journey, *r.experience.secondary_journeys] if c]
    card = next(c for c in cards if c.type == journey)
    return {a.id: a for a in card.actions}


# --- A.4 scenarios -----------------------------------------------------------


def test_electric_car_builds_step_by_step(seed: SeedData) -> None:
    deposit, page, simulation, search = run_scenario(seed, "electric_car")

    car = moment(deposit, MomentType.CAR_PROJECT)
    assert car is not None and car.confidence == pytest.approx(0.25) and car.status == MomentStatus.EMERGING
    assert deposit.decision.decision_type == DecisionType.WAIT
    assert deposit.experience.mode == "WAIT"

    assert moment(page, MomentType.CAR_PROJECT).confidence == pytest.approx(0.55)

    for r in (simulation, search):
        assert moment(r, MomentType.CAR_PROJECT).confidence >= 0.80
        assert r.decision.primary is not None and r.decision.primary.journey == JourneyType.CAR_PROJECT
        insurance = [a for a in card_actions(r, JourneyType.CAR_PROJECT).values() if a.kind == "PRODUCT"]
        assert insurance and all(a.status == ActionStatus.ALREADY_COVERED for a in insurance)
    confidences = [moment(r, MomentType.CAR_PROJECT).confidence for r in (deposit, page, simulation, search)]
    assert confidences == sorted(confidences)


def test_travel_covered_reassures_never_sells(seed: SeedData) -> None:
    for r in run_scenario(seed, "travel_covered"):
        assert MomentType.TRAVEL in {m.type for m in r.context.moments if m.status == MomentStatus.ACTIVE}
        assert r.decision.primary is not None and r.decision.primary.journey == JourneyType.TRAVEL_READY
        assert r.decision.decision_type == DecisionType.SHOW_SERVICE
        assert "You're already covered for your trip." in [n.text for n in r.experience.notices]
        actions = card_actions(r, JourneyType.TRAVEL_READY)
        assert actions["TRAVEL_INSURANCE"].status == ActionStatus.ALREADY_COVERED
        assert not any(a.kind == "PRODUCT" and a.status == ActionStatus.AVAILABLE for a in actions.values())


def test_travel_uncovered_offers_insurance(seed: SeedData) -> None:
    (r,) = run_scenario(seed, "travel_uncovered")
    assert JourneyType.TRAVEL_READY in shown(r)
    assert card_actions(r, JourneyType.TRAVEL_READY)["TRAVEL_INSURANCE"].status == ActionStatus.AVAILABLE


def test_cashflow_shock_suppresses_investing(seed: SeedData) -> None:
    interest, shock = run_scenario(seed, "cashflow_shock")

    assert intent_conf(interest, IntentType.START_INVESTING) >= 0.80
    assert JourneyType.INVESTMENT_START in shown(interest)

    assert moment(shock, MomentType.CASHFLOW_PRESSURE).confidence >= 0.70
    assert shock.decision.primary is not None and shock.decision.primary.journey == JourneyType.CASHFLOW_SUPPORT
    assert shock.decision.decision_type == DecisionType.SHOW_WARNING
    assert suppressed(shock)[JourneyType.INVESTMENT_START] == "CASHFLOW_RISK"
    assert JourneyType.INVESTMENT_START not in shown(shock)
    assert shock.context.snapshot.projected_balance_before_next_income == pytest.approx(287, abs=1)


def test_not_relevant_feedback_suppresses_journey(seed: SeedData) -> None:
    (r,) = run_scenario(seed, "not_relevant")
    assert suppressed(r)[JourneyType.FINANCIAL_FOUNDATION] == "FEEDBACK_DISMISSED"
    assert JourneyType.FINANCIAL_FOUNDATION not in shown(r)


def test_every_scenario_is_covered(seed: SeedData) -> None:
    tested = {"electric_car", "travel_covered", "travel_uncovered", "cashflow_shock", "not_relevant"}
    assert {s.id for s in seed.scenarios} == tested


# --- Principles --------------------------------------------------------------


@pytest.mark.parametrize("customer_id", ["lucas", "julie", "marc"])
def test_no_consent_means_no_action(seed: SeedData, customer_id: str) -> None:
    cust = customer(seed, customer_id).model_copy(update={"consent": Consent(personalization=False)})
    r = run_pipeline(cust, seed.events_by_customer[customer_id], NOW)
    assert r.decision.decision_type == DecisionType.NO_ACTION
    assert any(reason.startswith("NO_CONSENT") for reason in r.decision.reasons)
    assert r.context.signals == [] and r.context.moments == [] and r.intents == []
    assert r.experience.primary_journey is None


def test_parenthood_is_never_inferred_from_spending(seed: SeedData) -> None:
    """A clone of Julie without the declared event (baby purchases only) never gets NEW_PARENT active."""
    events = [e for e in seed.events_by_customer["julie"] if e.type != EventType.DECLARED_LIFE_EVENT]
    assert any(getattr(e.data, "category", None) == "baby_supplies" for e in events)
    r = run_pipeline(customer(seed, "julie"), events, NOW)
    parent = moment(r, MomentType.NEW_PARENT)
    assert parent is None or (parent.status != MomentStatus.ACTIVE and parent.confidence <= 0.35)
    assert JourneyType.FAMILY_START not in shown(r)


@pytest.mark.parametrize("customer_id", ["lucas", "julie", "marc", "claire"])
def test_pipeline_is_deterministic(customer_id: str) -> None:
    a, b = load_seed(NOW), load_seed(NOW)
    first = run_pipeline(customer(a, customer_id), a.events_by_customer[customer_id], NOW)
    second = run_pipeline(customer(b, customer_id), b.events_by_customer[customer_id], NOW)
    assert first.model_dump_json() == second.model_dump_json()


def test_engine_reacts_to_data_not_ids(seed: SeedData) -> None:
    """Claire's profile under a new id, fed Lucas's events, gets Lucas's outcome."""
    clone = customer(seed, "claire").model_copy(update={"id": "test_clone"})
    events = [e.model_copy(update={"customer_id": "test_clone"}) for e in seed.events_by_customer["lucas"]]
    r = run_pipeline(clone, events, NOW)
    assert moment(r, MomentType.FIRST_SALARY).confidence >= 0.80
    assert r.decision.primary is not None and r.decision.primary.journey == JourneyType.FINANCIAL_FOUNDATION
    # The clone keeps Claire's products: what she owns is never sold again.
    assert ProductType.pension_savings in clone.owned_products()
    assert card_actions(r, JourneyType.FINANCIAL_FOUNDATION)["LONG_TERM_PENSION_SAVINGS"].status == ActionStatus.ALREADY_COVERED


def test_same_data_under_another_id_gives_same_result(seed: SeedData) -> None:
    lucas = customer(seed, "lucas")
    clone = lucas.model_copy(update={"id": "test_clone"})
    events = [e.model_copy(update={"customer_id": "test_clone"}) for e in seed.events_by_customer["lucas"]]
    original = run_pipeline(lucas, seed.events_by_customer["lucas"], NOW)
    cloned = run_pipeline(clone, events, NOW)
    assert cloned.decision.model_dump_json() == original.decision.model_dump_json()
    assert cloned.intents == original.intents


def test_no_persona_name_in_engines_or_rules() -> None:
    pattern = re.compile(r"lucas|julie|marc|claire", re.IGNORECASE)
    offenders = [
        str(p.relative_to(APP_DIR))
        for folder in ("engines", "rules")
        for p in (APP_DIR / folder).rglob("*.py")
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []
