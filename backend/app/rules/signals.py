"""Signal rules: EVENT_SIGNAL_RULES, PATTERN_THRESHOLDS, SIGNAL_TTL_DAYS (A.9).

Owner: T2. Stub created by T0 (placeholder values, to be filled).
"""

from __future__ import annotations

from app.models.common import SignalType
from app.rules.schema import PatternThresholds, SignalEventRule

EVENT_SIGNAL_RULES: list[SignalEventRule] = []
PATTERN_THRESHOLDS = PatternThresholds()
DEFAULT_SIGNAL_TTL_DAYS = 60
SIGNAL_TTL_DAYS: dict[SignalType, int] = {}
