"""Clock, config, repositories, pipeline skeleton and /health. Owner: T0."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest
from conftest import NOW, make_customer, make_event, make_signal, make_snapshot
from fastapi.testclient import TestClient

from app.core.clock import FixedClock, SystemClock
from app.core.config import Settings
from app.main import app
from app.models.common import DecisionLevel, DecisionType
from app.models.decision import Decision
from app.models.experience import Hero, PersonalizedExperience, UnderTheHood
from app.repositories.base import EventLimitExceeded
from app.repositories.memory import InMemoryCustomerRepository, InMemoryEventRepository
from app.services.personalization_service import NO_CONSENT_REASON, Engines, run_pipeline

# --- Clock / config ------------------------------------------------------------------


def test_fixed_clock(fixed_clock):
    assert fixed_clock.now() == NOW
    fixed_clock.advance(days=1)
    assert fixed_clock.now() == NOW + timedelta(days=1)
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 1, 1))


def test_system_clock_is_aware():
    assert SystemClock().now().tzinfo is not None


def test_settings_defaults_and_env(monkeypatch):
    monkeypatch.delenv("KBC_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("KBC_DEMO_MODE", raising=False)
    s = Settings()
    assert s.cors_origins == ["http://localhost:3000"]
    assert s.demo_mode is True
    monkeypatch.setenv("KBC_CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("KBC_DEMO_MODE", "false")
    s = Settings()
    assert s.cors_origins == ["http://a.test", "http://b.test"]
    assert s.demo_mode is False


# --- Repositories ------------------------------------------------------------------------


def test_customer_repo_copies_and_reset():
    repo = InMemoryCustomerRepository([make_customer()])
    c = repo.get("test_customer")
    c.first_name = "Mutated"
    assert repo.get("test_customer").first_name == "Test"
    assert repo.get("nobody") is None
    assert repo.update_consent("test_customer", False).consent.personalization is False
    assert repo.get("test_customer").consent.personalization is False
    assert repo.update_consent("nobody", False) is None
    repo.reset("test_customer")
    assert repo.get("test_customer").consent.personalization is True
    assert [c.id for c in repo.list()] == ["test_customer"]


def test_event_repo_isolation_cap_and_reset():
    seed = {"test_customer": [make_event("PAGE_VIEW", {"page": "mortgage"})]}
    repo = InMemoryEventRepository(seed, max_events_per_customer=3)
    repo.append(make_event("PAGE_VIEW", {"page": "car_loan"}, origin="live"))
    repo.append(make_event("PAGE_VIEW", {"page": "car_loan"}, origin="live", customer_id="other"))
    assert len(repo.list_for("test_customer")) == 2
    assert [e.customer_id for e in repo.list_for("other")] == ["other"]
    assert repo.list_for("nobody") == []
    repo.append(make_event("PAGE_VIEW", {"page": "car_loan"}, origin="live"))
    with pytest.raises(EventLimitExceeded):
        repo.append(make_event("PAGE_VIEW", {"page": "car_loan"}, origin="live"))
    repo.reset("test_customer")
    assert len(repo.list_for("test_customer")) == 1
    assert len(repo.list_for("other")) == 1
    repo.reset()
    assert repo.list_for("other") == []


def test_event_repo_thread_safe_appends():
    repo = InMemoryEventRepository({}, max_events_per_customer=10_000)

    def worker():
        for _ in range(100):
            repo.append(make_event("PAGE_VIEW", {"page": "mortgage"}, origin="live"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(repo.list_for("test_customer")) == 800


# --- Pipeline skeleton with fake engines -----------------------------------------------------


class _FakeSignal:
    def extract_all(self, customer, events, snapshot, now):
        return [make_signal("SALARY_RECEIVED")]


class _FakeContext:
    def compute(self, customer, signals, now):
        return []


class _FakeIntent:
    def compute(self, customer, moments, signals, now):
        return []


class _FakeDecision:
    def __init__(self):
        self.events_seen = None

    def decide(self, customer, snapshot, moments, intents, events, now):
        self.events_seen = list(events)
        return Decision(
            decision_type=DecisionType.NO_ACTION, level=DecisionLevel.NONE, primary=None, secondary=[],
            considered=[], suppressed=[], reasons=["nothing to do"], decided_at=now,
        )


class _FakeExperience:
    def build(self, customer, context, intents, decision, now, events=()):
        return PersonalizedExperience(
            customer_id=customer.id, mode="CALM",
            hero=Hero(type="CALM", title="t", subtitle="s", tone="calm"),
            primary_journey=None, secondary_journeys=[], notices=[], why=[], checks=[],
            under_the_hood=UnderTheHood(
                persistent_context=context.persistent, products=context.products, snapshot=context.snapshot,
                signals=context.signals, moments=context.moments, intents=list(intents), decision=decision,
                timing={"computed_at": now.isoformat()},
            ),
            generated_at=now, disclaimer="d",
        )


def _fake_engines(decision=None):
    return Engines(
        snapshot=lambda customer, events, now: make_snapshot(as_of=now),
        signal=_FakeSignal(), context=_FakeContext(), intent=_FakeIntent(),
        decision=decision or _FakeDecision(), experience=_FakeExperience(),
    )


def test_run_pipeline_wires_engines_and_isolates_events():
    decision_engine = _FakeDecision()
    events = [make_event("PAGE_VIEW", {"page": "mortgage"}), make_event("PAGE_VIEW", {"page": "mortgage"}, customer_id="other")]
    result = run_pipeline(make_customer(), events, NOW, _fake_engines(decision_engine))
    assert [s.type for s in result.context.signals] == ["SALARY_RECEIVED"]
    assert [e.customer_id for e in decision_engine.events_seen] == ["test_customer"]
    assert result.experience.customer_id == "test_customer"
    result.model_dump_json()


def test_run_pipeline_no_consent():
    customer = make_customer(consent={"personalization": False})
    result = run_pipeline(customer, [], NOW, _fake_engines())
    assert result.decision.decision_type == DecisionType.NO_ACTION
    assert result.decision.reasons == [NO_CONSENT_REASON]
    assert result.decision.reasons[0].startswith("NO_CONSENT")
    assert result.context.signals == [] and result.context.moments == [] and result.intents == []


# --- API -------------------------------------------------------------------------------------------


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_now_constant_is_utc():
    assert NOW.tzinfo == UTC
