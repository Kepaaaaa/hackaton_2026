"""Signal Engine: events + history -> signals with evidence. Owner: T2.

- `extract`: one event -> signals, by generic matching of EVENT_SIGNAL_RULES.
- `detect_patterns`: history + snapshot -> signals, via the PATTERN_DETECTORS registry.
- `extract_all`: both, expired signals dropped, sorted by timestamp.

No moment or intent logic lives here.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.models.common import EventType, SignalType
from app.models.customer import Customer
from app.models.event import CustomerEvent
from app.models.signal import Signal
from app.models.snapshot import FinancialSnapshot
from app.rules import signals as signal_rules
from app.rules.schema import DataMatch, PatternThresholds, SignalEventRule

# Keywords shorter than this must match a whole word ("ev" must not match "every").
_PREFIX_KEYWORD_MIN_LEN = 4
_WORD_RE = re.compile(r"[a-z0-9]+")


class SignalEngine:
    def __init__(
        self,
        rules: Sequence[SignalEventRule] | None = None,
        thresholds: PatternThresholds | None = None,
        ttl_days: Mapping[SignalType, int] | None = None,
    ) -> None:
        self.rules = list(rules) if rules is not None else signal_rules.EVENT_SIGNAL_RULES
        self.thresholds = thresholds or signal_rules.PATTERN_THRESHOLDS
        self.ttl_days = dict(ttl_days) if ttl_days is not None else signal_rules.SIGNAL_TTL_DAYS

    def extract(self, event: CustomerEvent, now: datetime) -> list[Signal]:
        signals = []
        for rule in self.rules:
            if rule.event_type != event.type or not _rule_matches(rule, event):
                continue
            ttl = rule.ttl_days or self._ttl(rule.signal)
            signals.append(
                Signal(
                    type=rule.signal,
                    strength=rule.strength,
                    timestamp=event.timestamp,
                    expires_at=event.timestamp + timedelta(days=ttl),
                    source="event",
                    source_event_ids=[event.id],
                    description=_describe(rule, event, now),
                )
            )
        return signals

    def detect_patterns(
        self, customer: Customer, events: Sequence[CustomerEvent], snapshot: FinancialSnapshot, now: datetime
    ) -> list[Signal]:
        ctx = _PatternContext(
            events=sorted((e for e in events if e.timestamp <= now), key=lambda e: e.timestamp),
            snapshot=snapshot,
            now=now,
            t=self.thresholds,
        )
        signals = []
        for signal_type, detector in PATTERN_DETECTORS.items():
            hit = detector(ctx)
            if hit is None:
                continue
            signals.append(
                Signal(
                    type=signal_type,
                    strength=hit.strength,
                    timestamp=hit.timestamp,
                    expires_at=hit.timestamp + timedelta(days=self._ttl(signal_type)),
                    source="pattern",
                    source_event_ids=[e.id for e in hit.events],
                    description=hit.description,
                )
            )
        return signals

    def extract_all(
        self, customer: Customer, events: Sequence[CustomerEvent], snapshot: FinancialSnapshot, now: datetime
    ) -> list[Signal]:
        signals = [s for e in events if e.timestamp <= now for s in self.extract(e, now)]
        signals += self.detect_patterns(customer, events, snapshot, now)
        active = [s for s in signals if s.expires_at is None or s.expires_at > now]
        return sorted(active, key=lambda s: (s.timestamp, s.type.value))

    def _ttl(self, signal_type: SignalType) -> int:
        return self.ttl_days.get(signal_type, signal_rules.DEFAULT_SIGNAL_TTL_DAYS)


# --- Event rule matching --------------------------------------------------------------


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _match(cond: DataMatch, data: Any) -> bool:
    actual = _plain(getattr(data, cond.field, None))
    if actual is None:
        return False
    match cond.op:
        case "eq":
            return actual == cond.value
        case "in":
            return actual in cond.value  # type: ignore[operator]
        case "ge":
            return actual >= cond.value
        case "gt":
            return actual > cond.value
        case "le":
            return actual <= cond.value
        case _:
            return actual < cond.value


def _keyword_hit(keyword: str, words: list[str]) -> bool:
    if len(keyword) < _PREFIX_KEYWORD_MIN_LEN:
        return keyword in words
    return any(w.startswith(keyword) for w in words)


def _rule_matches(rule: SignalEventRule, event: CustomerEvent) -> bool:
    if not all(_match(cond, event.data) for cond in rule.match):
        return False
    if rule.keyword_groups:
        query = getattr(event.data, "query", None)
        if not isinstance(query, str):
            return False
        words = _WORD_RE.findall(query.lower())
        return all(any(_keyword_hit(k.lower(), words) for k in group) for group in rule.keyword_groups)
    return True


# --- Descriptions ------------------------------------------------------------------------


def _euros(amount: float) -> str:
    return f"€{amount:,.0f}" if float(amount).is_integer() else f"€{amount:,.2f}"


def _ago(ts: datetime, now: datetime) -> str:
    days = (now.date() - ts.date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def _humanize(value: Any) -> str:
    return str(_plain(value)).replace("_", " ")


class _Fields(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""


# Whitelisted template fields. The KBC search query is deliberately absent.
_FIELD_GETTERS: dict[str, Callable[[Any], str]] = {
    "amount": lambda d: _euros(d.amount) if getattr(d, "amount", None) is not None else "",
    "merchant": lambda d: getattr(d, "merchant", ""),
    "category": lambda d: _humanize(d.category) if hasattr(d, "category") else "",
    "page": lambda d: _humanize(d.page) if hasattr(d, "page") else "",
    "simulation_type": lambda d: _humanize(d.simulation_type) if hasattr(d, "simulation_type") else "",
    "product": lambda d: _humanize(d.product) if hasattr(d, "product") else "",
    "life_event": lambda d: _humanize(d.life_event) if hasattr(d, "life_event") else "",
}


def _describe(rule: SignalEventRule, event: CustomerEvent, now: datetime) -> str:
    template = rule.description or f"{_humanize(rule.signal).capitalize()}, {{ago}}"
    fields = _Fields({name: get(event.data) for name, get in _FIELD_GETTERS.items()})
    fields["ago"] = _ago(event.timestamp, now)
    return template.format_map(fields)


# --- Pattern detectors ------------------------------------------------------------------


@dataclass(frozen=True)
class _PatternContext:
    events: list[CustomerEvent]  # sorted by timestamp, none after `now`
    snapshot: FinancialSnapshot
    now: datetime
    t: PatternThresholds

    def ago(self, days: float) -> datetime:
        return self.now - timedelta(days=days)

    def credits(self, category: str) -> list[CustomerEvent]:
        return [
            e for e in self.events
            if e.type == EventType.TRANSACTION and e.data.direction == "in" and e.data.category == category
        ]


@dataclass(frozen=True)
class _PatternHit:
    strength: float
    timestamp: datetime
    description: str
    events: Sequence[CustomerEvent] = ()


def _first_recurring_salary(ctx: _PatternContext) -> _PatternHit | None:
    salaries = ctx.credits("salary")
    recent = [e for e in salaries if e.timestamp > ctx.ago(ctx.t.first_salary_recent_days)]
    if not recent:
        return None
    first = recent[0]
    lookback_start = first.timestamp - timedelta(days=ctx.t.first_salary_lookback_days)
    if any(lookback_start <= e.timestamp < first.timestamp for e in salaries):
        return None
    return _PatternHit(
        1.0,
        first.timestamp,
        f"First salary credit ({_euros(first.data.amount)}) with no salary in the "
        f"{ctx.t.first_salary_lookback_days} days before",
        [first],
    )


def _salary_stopped(ctx: _PatternContext) -> _PatternHit | None:
    salaries = ctx.credits("salary")
    history = [
        e for e in salaries
        if ctx.ago(ctx.t.salary_stopped_history_max_days) <= e.timestamp <= ctx.ago(ctx.t.salary_stopped_history_min_days)
    ]
    if not history or any(e.timestamp > ctx.ago(ctx.t.salary_stopped_quiet_days) for e in salaries):
        return None
    last = salaries[-1]
    became_true = min(last.timestamp + timedelta(days=ctx.t.salary_stopped_quiet_days), ctx.now)
    days = (ctx.now.date() - last.timestamp.date()).days
    return _PatternHit(1.0, became_true, f"No salary received for {days} days after regular salary credits", history)


def _recurring_pension_started(ctx: _PatternContext) -> _PatternHit | None:
    pensions = ctx.credits("pension")
    recent = [e for e in pensions if e.timestamp > ctx.ago(ctx.t.pension_recent_days)]
    if not recent or any(e.timestamp < ctx.ago(ctx.t.pension_no_prior_before_days) for e in pensions):
        return None
    new = [e for e in pensions if e.timestamp >= ctx.ago(ctx.t.pension_no_prior_before_days)]
    return _PatternHit(
        1.0,
        new[0].timestamp,
        f"Pension of {_euros(recent[-1].data.amount)} received, {len(new)} payment(s) since it started",
        new,
    )


def _new_recurring_child_expenses(ctx: _PatternContext) -> _PatternHit | None:
    child = [
        e for e in ctx.events
        if e.type == EventType.TRANSACTION
        and e.data.direction == "out"
        and e.data.category in ctx.t.child_expense_categories
    ]
    window_start = ctx.ago(ctx.t.child_expense_window_days)
    recent = [e for e in child if e.timestamp > window_start]
    if len(recent) < ctx.t.child_expense_min_count or len(recent) != len(child):
        return None
    return _PatternHit(
        ctx.t.child_expense_strength,
        recent[ctx.t.child_expense_min_count - 1].timestamp,
        f"{len(recent)} new child-related payments in the last {ctx.t.child_expense_window_days} days",
        recent,
    )


def _repeated_mortgage_simulation(ctx: _PatternContext) -> _PatternHit | None:
    sims = [
        e for e in ctx.events
        if e.type == EventType.SIMULATION
        and e.data.simulation_type == "mortgage"
        and e.timestamp > ctx.ago(ctx.t.mortgage_simulation_window_days)
    ]
    if len(sims) < ctx.t.mortgage_simulation_min_count:
        return None
    return _PatternHit(
        1.0,
        sims[ctx.t.mortgage_simulation_min_count - 1].timestamp,
        f"{len(sims)} mortgage simulations in the last {ctx.t.mortgage_simulation_window_days} days",
        sims,
    )


def _low_projected_balance(ctx: _PatternContext) -> _PatternHit | None:
    s = ctx.snapshot
    projected = s.projected_balance_before_next_income
    if not (
        projected < ctx.t.low_projected_balance_abs
        or projected < ctx.t.low_projected_balance_ratio * s.avg_monthly_spending
    ):
        return None
    return _PatternHit(
        1.0, ctx.now, f"Projected balance of {_euros(projected)} before the next income in {s.days_until_next_income} days"
    )


def _low_emergency_buffer(ctx: _PatternContext) -> _PatternHit | None:
    months = ctx.snapshot.emergency_buffer_months
    if months >= ctx.t.low_emergency_buffer_months:
        return None
    return _PatternHit(
        1.0, ctx.now, f"Savings cover {months:.1f} months of spending (below {ctx.t.low_emergency_buffer_months:g})"
    )


def _high_idle_cash(ctx: _PatternContext) -> _PatternHit | None:
    s = ctx.snapshot
    if s.idle_cash < ctx.t.high_idle_cash_min or s.idle_ratio < ctx.t.high_idle_ratio_min:
        return None
    return _PatternHit(
        1.0, ctx.now, f"{_euros(s.idle_cash)} ({s.idle_ratio:.0%} of liquid balance) above a 6-month cushion"
    )


PATTERN_DETECTORS: dict[SignalType, Callable[[_PatternContext], _PatternHit | None]] = {
    SignalType.FIRST_RECURRING_SALARY: _first_recurring_salary,
    SignalType.SALARY_STOPPED: _salary_stopped,
    SignalType.RECURRING_PENSION_STARTED: _recurring_pension_started,
    SignalType.NEW_RECURRING_CHILD_EXPENSES: _new_recurring_child_expenses,
    SignalType.REPEATED_MORTGAGE_SIMULATION: _repeated_mortgage_simulation,
    SignalType.LOW_PROJECTED_BALANCE: _low_projected_balance,
    SignalType.LOW_EMERGENCY_BUFFER: _low_emergency_buffer,
    SignalType.HIGH_IDLE_CASH: _high_idle_cash,
}
