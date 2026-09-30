"""API happy paths (T5). The app runs on seed data with a fixed clock."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest
from conftest import NOW
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.core.config import Settings
from app.main import create_app
from app.models.common import DecisionType, MomentType
from app.services.personalization_service import PersonalizationService

CUSTOMERS = ["lucas", "julie", "marc", "claire"]
MY_KBC_KEYS = {"customer", "profile", "snapshot", "moments", "intents", "decision", "experience"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    service = PersonalizationService.from_seed(FixedClock(NOW))
    with TestClient(create_app(Settings(), service)) as c:
        yield c


def moment_confidence(payload: dict, moment: MomentType) -> float:
    return next((m["confidence"] for m in payload["moments"] if m["type"] == moment), 0.0)


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_customers(client: TestClient) -> None:
    body = client.get("/customers").json()
    assert [c["id"] for c in body] == CUSTOMERS
    assert all(set(c) == {"id", "first_name", "age", "headline"} for c in body)
    assert body[0]["headline"] == "Young professional, tenant"


@pytest.mark.parametrize("customer_id", CUSTOMERS)
@pytest.mark.parametrize("suffix", ["", "/overview", "/context", "/intents", "/decision", "/experience", "/my-kbc"])
def test_read_endpoints(client: TestClient, customer_id: str, suffix: str) -> None:
    r = client.get(f"/customers/{customer_id}{suffix}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


def test_my_kbc_shape(client: TestClient) -> None:
    body = client.get("/customers/lucas/my-kbc").json()
    assert set(body) == MY_KBC_KEYS
    assert body["decision"]["primary"]["journey"] == "FINANCIAL_FOUNDATION"
    for key in ("hero", "primary_journey", "notices", "why", "checks", "under_the_hood", "disclaimer"):
        assert key in body["experience"]


def test_calm_customer(client: TestClient) -> None:
    body = client.get("/customers/claire/my-kbc").json()
    assert body["decision"]["decision_type"] == DecisionType.NO_ACTION
    assert body["experience"]["mode"] == "CALM"
    assert body["experience"]["hero"]["title"] == "Everything looks on track."


def test_overview_is_generic(client: TestClient) -> None:
    lucas = client.get("/customers/lucas/overview").json()
    marc = client.get("/customers/marc/overview").json()
    assert lucas["banners"] == marc["banners"]
    assert len(lucas["recent_transactions"]) == 10
    stamps = [t["timestamp"] for t in lucas["recent_transactions"]]
    assert stamps == sorted(stamps, reverse=True)
    assert "decision" not in lucas and "experience" not in lucas


def test_overview_balance_follows_live_transactions(client: TestClient) -> None:
    def current() -> float:
        accounts = client.get("/customers/lucas/overview").json()["accounts"]
        return next(a["balance"] for a in accounts if a["type"] == "current")

    before = current()
    tx = {"type": "TRANSACTION", "data": {"direction": "out", "amount": 100, "category": "leisure", "merchant": "Cinema"}}
    assert client.post("/customers/lucas/events", json=tx).status_code == 200
    assert current() == pytest.approx(before - 100)


def test_car_scenario_step_by_step_through_events(client: TestClient) -> None:
    steps = [
        {"type": "TRANSACTION", "data": {"direction": "out", "amount": 500, "category": "automotive", "merchant": "EV Motors"}},
        {"type": "PAGE_VIEW", "data": {"page": "electric_car_loan"}},
        {"type": "SIMULATION", "data": {"simulation_type": "electric_car_loan", "amount": 25000, "duration_months": 60}},
    ]
    confidences = []
    decisions = []
    for event in steps:
        body = client.post("/customers/claire/events", json=event).json()
        assert set(body) == MY_KBC_KEYS
        confidences.append(moment_confidence(body, MomentType.CAR_PROJECT))
        decisions.append(body["decision"])
    assert confidences[0] == pytest.approx(0.25)
    assert confidences == sorted(confidences) and confidences[-1] >= 0.80
    assert decisions[0]["decision_type"] == DecisionType.WAIT
    assert decisions[-1]["primary"]["journey"] == "CAR_PROJECT"

    card = client.get("/customers/claire/experience").json()["primary_journey"]
    insurance = next(a for a in card["actions"] if a["id"] == "CAR_INSURANCE_STATUS")
    assert insurance["status"] == "ALREADY_COVERED"


def test_simulated_loan_amount_reaches_the_payload(client: TestClient) -> None:
    for step in (1, 2):
        client.post("/customers/claire/scenarios/electric_car/steps/%d" % step)
    sim = {"type": "SIMULATION", "data": {"simulation_type": "electric_car_loan", "amount": 40000, "duration_months": 48}}
    card = client.post("/customers/claire/events", json=sim).json()["experience"]["primary_journey"]
    loan = next(a for a in card["actions"] if a["id"] == "CAR_LOAN_SIMULATION")
    assert 40000 in loan["payload"].values()
    assert 48 in loan["payload"].values()


def test_live_events_get_server_ids(client: TestClient) -> None:
    event = {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "days_ago": 3}
    client.post("/customers/lucas/events", json=event)
    client.post("/customers/lucas/events", json=event)
    service: PersonalizationService = client.app.state.service
    live = [e for e in service.list_events("lucas") if e.origin == "live"]
    assert [e.id for e in live] == ["evt_lucas_live_0001", "evt_lucas_live_0002"]
    assert live[0].timestamp == NOW - timedelta(days=3)


def test_reset_restores_seed_state(client: TestClient) -> None:
    original = client.get("/customers/lucas/my-kbc").json()
    client.post("/customers/lucas/scenarios/cashflow_shock/steps/1")
    changed = client.post("/customers/lucas/scenarios/cashflow_shock/steps/2").json()
    assert changed["decision"]["primary"]["journey"] == "CASHFLOW_SUPPORT"
    restored = client.post("/customers/lucas/reset").json()
    assert restored == original


def test_feedback_changes_the_decision(client: TestClient) -> None:
    before = client.get("/customers/lucas/decision").json()
    assert before["primary"]["journey"] == "FINANCIAL_FOUNDATION"
    after = client.post("/customers/lucas/feedback", json={"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}).json()
    primary = after["decision"]["primary"]
    assert primary is None or primary["journey"] != "FINANCIAL_FOUNDATION"
    suppressed = {s["journey"]: s["rule"] for s in after["decision"]["suppressed"]}
    assert suppressed["FINANCIAL_FOUNDATION"] == "FEEDBACK_DISMISSED"


def test_consent_off_then_on(client: TestClient) -> None:
    off = client.put("/customers/lucas/consent", json={"personalization": False}).json()
    assert off["decision"]["decision_type"] == DecisionType.NO_ACTION
    assert any("NO_CONSENT" in r for r in off["decision"]["reasons"])
    assert off["moments"] == [] and off["intents"] == []
    on = client.put("/customers/lucas/consent", json={"personalization": True}).json()
    assert on["decision"]["primary"]["journey"] == "FINANCIAL_FOUNDATION"


def test_reset_restores_consent(client: TestClient) -> None:
    client.put("/customers/lucas/consent", json={"personalization": False})
    assert client.post("/customers/lucas/reset").json()["customer"]["consent"]["personalization"] is True


def test_list_scenarios(client: TestClient) -> None:
    body = client.get("/scenarios").json()
    ids = {s["id"] for s in body}
    assert {"electric_car", "travel_covered", "travel_uncovered", "cashflow_shock", "not_relevant"} <= ids
    car = next(s for s in body if s["id"] == "electric_car")
    assert [s["step"] for s in car["steps"]] == [1, 2, 3, 4]


def test_scenario_for_another_customer_is_rejected(client: TestClient) -> None:
    r = client.post("/customers/lucas/scenarios/electric_car/steps/1")
    assert r.status_code == 404


def test_scenario_step_out_of_range(client: TestClient) -> None:
    assert client.post("/customers/claire/scenarios/electric_car/steps/5").status_code == 404
    assert client.post("/customers/claire/scenarios/electric_car/steps/0").status_code == 422


def test_reads_are_cached_and_writes_invalidate(client: TestClient) -> None:
    service: PersonalizationService = client.app.state.service
    first = service.get_state("lucas")
    assert service.get_state("lucas") is first
    client.post("/customers/lucas/events", json={"type": "PAGE_VIEW", "data": {"page": "car_loan"}})
    assert service.get_state("lucas") is not first


def test_openapi_lists_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for p in (
        "/customers",
        "/customers/{customer_id}/my-kbc",
        "/customers/{customer_id}/events",
        "/customers/{customer_id}/feedback",
        "/customers/{customer_id}/consent",
        "/customers/{customer_id}/reset",
        "/scenarios",
        "/customers/{customer_id}/scenarios/{scenario_id}/steps/{step}",
        "/health",
    ):
        assert p in paths
