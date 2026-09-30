"""Context Engine: signals -> Active Moments (confidence + TTL). Owner: T3.

Generic loop over MOMENT_RULES: no moment name appears in this file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from app.engines.scoring import Contributor, weighted_sum
from app.models.common import MomentStatus, MomentType, SignalType
from app.models.context import ActiveMoment
from app.models.customer import Customer
from app.models.signal import Signal
from app.rules import moments as moment_rules
from app.rules.schema import MomentRule


def _is_live(signal: Signal, window_start: datetime, now: datetime) -> bool:
    if signal.timestamp > now or signal.timestamp < window_start:
        return False
    return signal.expires_at is None or signal.expires_at > now


class ContextEngine:
    def __init__(
        self,
        rules: Sequence[MomentRule] | None = None,
        active_threshold: float = moment_rules.ACTIVE_THRESHOLD,
        emerging_threshold: float = moment_rules.EMERGING_THRESHOLD,
        required_explanations: Mapping[MomentType, str] | None = None,
    ) -> None:
        self.rules = list(rules) if rules is not None else moment_rules.MOMENT_RULES
        self.active_threshold = active_threshold
        self.emerging_threshold = emerging_threshold
        self.required_explanations = (
            required_explanations if required_explanations is not None else moment_rules.REQUIRED_SIGNAL_EXPLANATIONS
        )

    def compute(self, customer: Customer, signals: Sequence[Signal], now: datetime) -> list[ActiveMoment]:
        moments = [m for rule in self.rules if (m := self._evaluate(rule, signals, now)) is not None]
        return sorted(moments, key=lambda m: (-m.confidence, m.type.value))

    def _evaluate(self, rule: MomentRule, signals: Sequence[Signal], now: datetime) -> ActiveMoment | None:
        ttl = timedelta(days=rule.ttl_days)
        window_start = now - ttl

        # Strongest (effective) signal per type; ties go to the most recent one.
        best: dict[SignalType, tuple[float, Signal]] = {}
        for s in signals:
            if s.type not in rule.signal_weights or not _is_live(s, window_start, now):
                continue
            value = self._decayed(rule, s, now)
            current = best.get(s.type)
            if current is None or (value, s.timestamp) > (current[0], current[1].timestamp):
                best[s.type] = (value, s)
        if not best:
            return None

        contributors = [
            Contributor(
                ref=signal_type.value,
                kind="signal",
                weight=rule.signal_weights[signal_type],
                value=value,
                detail=f"{s.description} (strength {value:.2f} × weight {rule.signal_weights[signal_type]:.2f})",
                source_event_ids=list(s.source_event_ids),
            )
            for signal_type, (value, s) in sorted(best.items(), key=lambda kv: -rule.signal_weights[kv[0]])
        ]

        cap, cap_ref, cap_detail = 1.0, "cap", "Confidence capped at 1.0"
        if rule.requires_any and not any(t in best for t in rule.requires_any):
            cap = rule.cap_without_required
            cap_ref = "requires_any"
            required = ", ".join(t.value for t in rule.requires_any)
            explanation = self.required_explanations.get(rule.moment, f"Requires one of: {required}")
            cap_detail = f"{explanation} (capped at {cap:.2f})"

        confidence, evidence = weighted_sum(contributors, cap=cap, cap_ref=cap_ref, cap_detail=cap_detail)
        if confidence < self.emerging_threshold:
            return None

        timestamps = [s.timestamp for _, s in best.values()]
        return ActiveMoment(
            type=rule.moment,
            confidence=confidence,
            status=MomentStatus.ACTIVE if confidence >= self.active_threshold else MomentStatus.EMERGING,
            detected_at=min(timestamps),
            expires_at=max(timestamps) + ttl,
            evidence=evidence,
        )

    @staticmethod
    def _decayed(rule: MomentRule, signal: Signal, now: datetime) -> float:
        if rule.decay == "none":
            return signal.strength
        age_days = (now - signal.timestamp).total_seconds() / 86400
        return round(signal.strength * max(0.0, 1 - age_days / rule.ttl_days), 4)
