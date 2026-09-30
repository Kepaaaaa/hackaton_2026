"""Intent Engine: moments + signals + profile -> several intents. Owner: T3.

Generic loop over INTENT_RULES: no intent or moment name appears in this file.
Only ACTIVE moments contribute; EMERGING ones stay visible but drive nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.engines.scoring import Contributor, weighted_sum
from app.models.common import MomentStatus, MomentType, SignalType
from app.models.context import ActiveMoment
from app.models.customer import Customer, CustomerProfile
from app.models.intent import Intent
from app.models.signal import Signal
from app.rules import intents as intent_rules
from app.rules.schema import IntentRule

_MISSING = object()


def resolve_path(profile: CustomerProfile, path: str) -> Any:
    """Read a dotted attribute path on the profile; returns `_MISSING` if absent."""
    value: Any = profile
    for part in path.split("."):
        value = getattr(value, part, _MISSING)
        if value is _MISSING:
            return _MISSING
    return value


def path_exists(path: str) -> bool:
    """True if `path` is a field path of CustomerProfile (checked on the model schema)."""
    model: Any = CustomerProfile
    for part in path.split("."):
        fields = getattr(model, "model_fields", None)
        if not fields or part not in fields:
            return False
        model = fields[part].annotation
    return True


class IntentEngine:
    def __init__(
        self,
        rules: Sequence[IntentRule] | None = None,
        min_confidence: float = intent_rules.INTENT_MIN_CONFIDENCE,
    ) -> None:
        self.rules = list(rules) if rules is not None else intent_rules.INTENT_RULES
        self.min_confidence = min_confidence

    def compute(
        self, customer: Customer, moments: Sequence[ActiveMoment], signals: Sequence[Signal], now: datetime
    ) -> list[Intent]:
        active: dict[MomentType, ActiveMoment] = {}
        for m in moments:
            if m.status == MomentStatus.ACTIVE and (m.type not in active or m.confidence > active[m.type].confidence):
                active[m.type] = m

        strongest: dict[SignalType, Signal] = {}
        for s in signals:
            if s.timestamp > now or (s.expires_at is not None and s.expires_at <= now):
                continue
            if s.type not in strongest or s.strength > strongest[s.type].strength:
                strongest[s.type] = s

        intents = [i for rule in self.rules if (i := self._evaluate(rule, customer, active, strongest)) is not None]
        return sorted(intents, key=lambda i: (-i.confidence, i.type.value))

    def _evaluate(
        self,
        rule: IntentRule,
        customer: Customer,
        active: dict[MomentType, ActiveMoment],
        strongest: dict[SignalType, Signal],
    ) -> Intent | None:
        contributors: list[Contributor] = []
        related: list[MomentType] = []
        for moment_type, weight in rule.moment_weights.items():
            m = active.get(moment_type)
            if m is None:
                continue
            related.append(moment_type)
            contributors.append(
                Contributor(
                    ref=moment_type.value,
                    kind="moment",
                    weight=weight,
                    value=m.confidence,
                    detail=f"Moment {moment_type.value} (confidence {m.confidence:.2f} × weight {weight:.2f})",
                    source_event_ids=sorted({eid for e in m.evidence for eid in e.source_event_ids}),
                )
            )
        for signal_type, weight in rule.signal_weights.items():
            s = strongest.get(signal_type)
            if s is None:
                continue
            contributors.append(
                Contributor(
                    ref=signal_type.value,
                    kind="signal",
                    weight=weight,
                    value=s.strength,
                    detail=f"{s.description} (strength {s.strength:.2f} × weight {weight:.2f})",
                    source_event_ids=list(s.source_event_ids),
                )
            )
        # Profile adjustments only nudge an intent that already has evidence behind it.
        if not contributors:
            return None
        for adj in rule.profile_adjustments:
            if resolve_path(customer.profile, adj.path) == adj.equals:
                contributors.append(
                    Contributor(
                        ref=adj.path,
                        kind="profile",
                        weight=adj.delta,
                        value=1.0,
                        detail=f"Profile {adj.path} = {adj.equals} ({adj.delta:+.2f})",
                    )
                )

        confidence, evidence = weighted_sum(contributors, cap=1.0, floor=0.0)
        if confidence < self.min_confidence:
            return None
        return Intent(type=rule.intent, confidence=confidence, related_moments=related, evidence=evidence)
