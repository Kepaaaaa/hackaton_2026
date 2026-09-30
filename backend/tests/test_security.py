"""Security behaviour of the API (T5, A.10)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from conftest import NOW
from fastapi.testclient import TestClient

from app.api.deps import get_service
from app.core.clock import FixedClock
from app.core.config import Settings
from app.main import create_app
from app.services.personalization_service import PersonalizationService


def make_client(**settings: object) -> TestClient:
    service = PersonalizationService.from_seed(FixedClock(NOW))
    return TestClient(create_app(Settings(**settings), service))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with make_client() as c:
        yield c


def assert_error(r, status: int, code: str) -> dict:
    assert r.status_code == status
    body = r.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    return body


@pytest.mark.parametrize("customer_id", ["nobody", "Lucas", "a", "x" * 40, "lucas;drop", "..%2Fetc"])
def test_unknown_or_invalid_id_is_a_neutral_404(client: TestClient, customer_id: str) -> None:
    for suffix in ("", "/my-kbc", "/context"):
        r = client.get(f"/customers/{customer_id}{suffix}")
        body = assert_error(r, 404, "NOT_FOUND")
        assert body["error"]["message"] == "Resource not found."
        if len(customer_id) > 3:
            assert customer_id not in r.text


def test_unknown_id_on_post_is_404(client: TestClient) -> None:
    r = client.post("/customers/nobody/events", json={"type": "PAGE_VIEW", "data": {"page": "car_loan"}})
    assert_error(r, 404, "NOT_FOUND")


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    assert_error(client.get("/does-not-exist"), 404, "NOT_FOUND")


@pytest.mark.parametrize(
    "body",
    [
        {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "admin": True},
        {"type": "PAGE_VIEW", "data": {"page": "car_loan", "extra": 1}},
        {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "id": "evt_forged"},
        {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "timestamp": "2020-01-01T00:00:00Z"},
        {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "origin": "seed"},
        {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "customer_id": "julie"},
    ],
)
def test_extra_and_server_fields_are_rejected(client: TestClient, body: dict) -> None:
    assert_error(client.post("/customers/lucas/events", json=body), 422, "VALIDATION_ERROR")


def test_extra_fields_rejected_on_feedback_and_consent(client: TestClient) -> None:
    fb = {"journey": "FINANCIAL_FOUNDATION", "feedback": "LATER", "x": 1}
    assert_error(client.post("/customers/lucas/feedback", json=fb), 422, "VALIDATION_ERROR")
    assert_error(client.put("/customers/lucas/consent", json={"personalization": False, "x": 1}), 422, "VALIDATION_ERROR")
    assert_error(client.put("/customers/lucas/consent", json={}), 422, "VALIDATION_ERROR")


@pytest.mark.parametrize("days_ago", [366, -1, 10_000])
def test_days_ago_is_bounded(client: TestClient, days_ago: int) -> None:
    body = {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, "days_ago": days_ago}
    assert_error(client.post("/customers/lucas/events", json=body), 422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "data",
    [
        {"direction": "out", "amount": 0, "category": "leisure", "merchant": "M"},
        {"direction": "out", "amount": 2_000_000, "category": "leisure", "merchant": "M"},
        {"direction": "out", "amount": 10, "category": "bitcoin", "merchant": "M"},
        {"direction": "out", "amount": 10, "category": "leisure", "merchant": "M" * 81},
    ],
)
def test_transaction_bounds(client: TestClient, data: dict) -> None:
    assert_error(client.post("/customers/lucas/events", json={"type": "TRANSACTION", "data": data}), 422, "VALIDATION_ERROR")


def test_422_never_echoes_the_input(client: TestClient) -> None:
    marker = "SECRET_MARKER_4242"
    bodies = [
        {"type": "KBC_SEARCH", "data": {"query": marker + "\x00"}},
        {"type": "KBC_SEARCH", "data": {"query": marker * 10}},
        {"type": "PAGE_VIEW", "data": {"page": marker}},
        {"type": marker, "data": {}},
        {"type": "PAGE_VIEW", "data": {"page": "car_loan"}, marker: marker},
    ]
    for body in bodies:
        r = client.post("/customers/lucas/events", json=body)
        assert r.status_code == 422
        assert marker not in r.text
        for detail in r.json()["error"]["details"]:
            assert set(detail) == {"loc", "msg"}


def test_malformed_json_is_422(client: TestClient) -> None:
    r = client.post("/customers/lucas/events", content=b"{not json", headers={"content-type": "application/json"})
    assert_error(r, 422, "VALIDATION_ERROR")


def test_search_query_is_never_echoed_in_the_response(client: TestClient) -> None:
    query = "unique query 9f3a"
    r = client.post("/customers/lucas/events", json={"type": "KBC_SEARCH", "data": {"query": query}})
    assert r.status_code == 200
    assert query not in r.text


def test_oversized_body_is_rejected(client: TestClient) -> None:
    big = {"type": "KBC_SEARCH", "data": {"query": "a"}, "pad": "x" * 20_000}
    assert_error(client.post("/customers/lucas/events", json=big), 413, "PAYLOAD_TOO_LARGE")


def test_oversized_body_without_content_length_is_rejected(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(20):
            yield b"x" * 1024

    r = client.post("/customers/lucas/events", content=chunks(), headers={"content-type": "application/json"})
    assert_error(r, 413, "PAYLOAD_TOO_LARGE")


def test_event_log_is_capped() -> None:
    service = PersonalizationService.from_seed(FixedClock(NOW), max_events_per_customer=160)
    with TestClient(create_app(Settings(), service)) as c:
        event = {"type": "PAGE_VIEW", "data": {"page": "car_loan"}}
        statuses = [c.post("/customers/lucas/events", json=event).status_code for _ in range(60)]
        assert 429 in statuses
        assert_error(c.post("/customers/lucas/events", json=event), 429, "TOO_MANY_EVENTS")
        assert c.get("/customers/lucas/my-kbc").status_code == 200


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/scenarios"),
        ("post", "/customers/claire/scenarios/electric_car/steps/1"),
        ("post", "/customers/lucas/reset"),
    ],
)
def test_demo_endpoints_hidden_when_demo_mode_off(method: str, path: str) -> None:
    with make_client(demo_mode=False) as c:
        assert_error(getattr(c, method)(path), 404, "NOT_FOUND")
        assert c.get("/customers/lucas/my-kbc").status_code == 200


def test_no_stack_trace_on_500() -> None:
    app = create_app(Settings(), PersonalizationService.from_seed(FixedClock(NOW)))

    class Broken:
        def get_customer(self, _: str) -> None:
            raise RuntimeError("database password is hunter2")

    app.dependency_overrides[get_service] = lambda: Broken()
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/customers/lucas/my-kbc")
    assert_error(r, 500, "INTERNAL_ERROR")
    assert "hunter2" not in r.text and "Traceback" not in r.text and "RuntimeError" not in r.text


def test_security_headers(client: TestClient) -> None:
    for path in ("/health", "/customers/lucas/my-kbc", "/customers/nobody"):
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "no-referrer"
    assert client.get("/customers/lucas/my-kbc").headers["cache-control"] == "no-store"
    assert client.get("/customers").headers["cache-control"] == "no-store"


def test_cors_allows_only_configured_origins() -> None:
    with make_client(KBC_CORS_ORIGINS="http://front.example") as c:
        ok = c.get("/health", headers={"origin": "http://front.example"})
        bad = c.get("/health", headers={"origin": "http://evil.example"})
    assert ok.headers["access-control-allow-origin"] == "http://front.example"
    assert "access-control-allow-origin" not in bad.headers


def test_customer_isolation(client: TestClient) -> None:
    merchant = "Isolation Test Merchant"
    tx = {"type": "TRANSACTION", "data": {"direction": "out", "amount": 42, "category": "leisure", "merchant": merchant}}
    assert client.post("/customers/lucas/events", json=tx).status_code == 200
    assert merchant in client.get("/customers/lucas/overview").text
    for other in ("julie", "marc", "claire"):
        for suffix in ("/overview", "/context", "/my-kbc", "/experience"):
            text = client.get(f"/customers/{other}{suffix}").text
            assert merchant not in text
            assert "evt_lucas" not in text
