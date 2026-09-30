"""Generic weighted aggregation with evidence, shared by the context and intent engines.

Owner: T3.

`weighted_sum` turns a list of contributors into a clamped score and one Evidence per
contributor. The evidence contributions always add up to the returned score: when the
raw sum is clamped, a `rule` evidence carries the (negative or positive) difference.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.models.common import Evidence

EvidenceKind = Literal["signal", "moment", "profile", "product", "feedback", "financial", "rule"]

PRECISION = 4


@dataclass(frozen=True)
class Contributor:
    ref: str
    kind: EvidenceKind
    weight: float
    value: float
    detail: str
    source_event_ids: list[str] = field(default_factory=list)

    @property
    def contribution(self) -> float:
        return round(self.weight * self.value, PRECISION)


def weighted_sum(
    contributors: Sequence[Contributor],
    cap: float = 1.0,
    floor: float = 0.0,
    cap_ref: str = "cap",
    cap_detail: str | None = None,
) -> tuple[float, list[Evidence]]:
    """Return (score, evidence). score = clamp(Σ weight × value, floor, cap)."""
    evidence = [
        Evidence(
            kind=c.kind,
            ref=c.ref,
            contribution=c.contribution,
            detail=c.detail,
            source_event_ids=list(c.source_event_ids),
        )
        for c in contributors
    ]
    raw = round(sum(e.contribution for e in evidence), PRECISION)
    score = min(cap, max(floor, raw))
    if score != raw:
        if raw > cap:
            ref, detail = cap_ref, cap_detail or f"Capped at {cap:g}"
        else:
            ref, detail = "floor", f"Raised to the floor of {floor:g}"
        evidence.append(
            Evidence(kind="rule", ref=ref, contribution=round(score - raw, PRECISION), detail=detail)
        )
    return round(score, PRECISION), evidence
