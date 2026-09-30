"""Decision weights, thresholds, timing curve, suppression rules, feedback windows (A.9).

Owner: T4. Stub created by T0 (placeholder values, to be filled).
"""

from __future__ import annotations

from app.rules.schema import DecisionThresholds, DecisionWeights, SuppressionRule

DECISION_WEIGHTS = DecisionWeights()
DECISION_THRESHOLDS = DecisionThresholds()
SUPPRESSION_RULES: list[SuppressionRule] = []
