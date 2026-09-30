"""Runs only when KBC_CONTEXT_BACKEND points at the backend/ folder of the KBC Context branch."""
import os

import pandas as pd
import pytest

from test_model import AS_OF, Builder

BACKEND = os.environ.get("KBC_CONTEXT_BACKEND")
pytestmark = pytest.mark.skipif(not BACKEND, reason="set KBC_CONTEXT_BACKEND to the backend/ folder")


def test_backend_pipeline_runs_on_contract_data_and_learned_rules_keep_the_privacy_cap():
    from kbcfit_ml.bridges.kbc_context import Bridge, learned_rules

    b = Builder().customer("C1")
    for d in ("2026-09-01", "2026-09-10", "2026-09-20"):
        b.pay("C1", d, -90, "baby", "Dreambaby")
    b.pay("C1", "2026-09-15", -18_000, "car_dealer", "Garage Maes")
    bridge = Bridge(BACKEND, b.tables())
    customer, events, now, signals = bridge.signals(0, pd.Timestamp(AS_OF))
    assert customer.id == "c1" and events
    types = {s.type.value for s in signals}
    assert {"CHILD_RELATED_EXPENSE", "AUTOMOTIVE_TRANSACTION"} <= types

    weights = {"moments": {"NEW_PARENT": {"learned": [0.9, 0.9, 0.9, 0.9, 0.9]}}}
    rules = learned_rules(bridge.mr, weights)
    engines = bridge.ps.Engines(context=bridge.ce.ContextEngine(rules=rules))
    moments = {m.type.value: m.confidence for m in bridge.ps.run_pipeline(customer, events, now, engines).context.moments}
    assert moments.get("NEW_PARENT", 0) <= 0.35        # never inferred without a declaration, whatever the weights
