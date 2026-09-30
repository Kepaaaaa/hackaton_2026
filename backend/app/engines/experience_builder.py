"""Experience Builder: decision -> structured PersonalizedExperience JSON (never HTML).

Owner: T4.

Mode comes from the decision, the hero from the primary journey's driving moment, cards
from the journey catalog (owned products -> ALREADY_COVERED, payloads from calculators),
texts from rules/copy.py. `checks` are always filled so a calm page still shows what was
verified.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from app.engines.calculators import run_calculator
from app.models.common import ActionStatus, DecisionLevel, DecisionType, JourneyType, MomentStatus, ProductType
from app.models.context import ActiveMoment, CustomerContext
from app.models.customer import Customer
from app.models.decision import Decision, JourneyCandidate
from app.models.event import CustomerEvent
from app.models.experience import (
    CheckItem,
    ExperienceAction,
    Hero,
    JourneyCard,
    Notice,
    PersonalizedExperience,
    UnderTheHood,
    WhyItem,
)
from app.models.intent import Intent
from app.models.journey import JourneyDef
from app.rules.copy import COPY, ExperienceCopy, HeroCopy
from app.rules.journeys import JOURNEYS

MAX_WHY = 4


class ExperienceBuilder:
    def __init__(
        self,
        journeys: Mapping[JourneyType, JourneyDef] | None = None,
        copy: ExperienceCopy | None = None,
    ) -> None:
        self.journeys = journeys if journeys is not None else JOURNEYS
        self.copy = copy or COPY

    def build(
        self,
        customer: Customer,
        context: CustomerContext,
        intents: Sequence[Intent],
        decision: Decision,
        now: datetime,
        events: Sequence[CustomerEvent] = (),
    ) -> PersonalizedExperience:
        """`events` is optional: only used to read the latest simulated amounts for calculators."""
        owned = set(customer.owned_products())
        cards = [self._card(c, context, owned, events) for c in ([decision.primary] if decision.primary else [])]
        cards += [self._card(c, context, owned, events) for c in decision.secondary]

        if not customer.consent.personalization:
            mode, hero, notices, why = "CALM", self._hero(self.copy.hero_no_consent, "NO_CONSENT"), \
                [Notice(kind="info", text=self.copy.no_consent_notice)], []
        elif decision.decision_type == DecisionType.WAIT:
            emerging = [m for m in context.moments if m.status == MomentStatus.EMERGING]
            mode, hero = "WAIT", self._hero(self.copy.hero_wait, "WAIT")
            notices = [Notice(kind="info", text=self.copy.wait_notice)]
            why = self._why_from_moments(emerging)
        elif decision.primary is None:
            mode, hero, notices = "CALM", self._hero(self.copy.hero_calm, "CALM"), []
            why = [WhyItem(text=self.copy.why_calm, contribution=0.0)]
        else:
            mode = decision.level.value if decision.level != DecisionLevel.NONE else "PASSIVE"
            moment = self._driving_moment(decision.primary, intents, context.moments)
            hero_copy = (self.copy.hero_by_moment.get(moment.type) if moment else None) or \
                self.copy.hero_by_journey[decision.primary.journey]
            hero = self._hero(hero_copy, moment.type.value if moment else decision.primary.journey.value)
            notices = self._notices(cards)
            why = self._why_from_moments([moment]) if moment else []
            if not why:
                why = [WhyItem(text=e.detail, contribution=e.contribution)
                       for e in decision.primary.evidence if e.contribution > 0][:MAX_WHY]

        return PersonalizedExperience(
            customer_id=customer.id,
            mode=mode,
            hero=hero,
            primary_journey=cards[0] if decision.primary else None,
            secondary_journeys=cards[1:] if decision.primary else [],
            notices=notices,
            why=why,
            checks=self._checks(context, decision, cards, owned),
            under_the_hood=UnderTheHood(
                persistent_context=context.persistent,
                products=context.products,
                snapshot=context.snapshot,
                signals=context.signals,
                moments=context.moments,
                intents=list(intents),
                decision=decision,
                timing=self._timing(context.moments, now),
            ),
            generated_at=now,
            disclaimer=self.copy.disclaimer,
        )

    # --- parts ---------------------------------------------------------------------------------

    @staticmethod
    def _hero(c: HeroCopy, type_: str) -> Hero:
        return Hero(type=type_, title=c.title, subtitle=c.subtitle, tone=c.tone)

    def _card(
        self,
        candidate: JourneyCandidate,
        context: CustomerContext,
        owned: set[ProductType],
        events: Sequence[CustomerEvent],
    ) -> JourneyCard:
        journey = self.journeys[candidate.journey]
        actions = [
            ExperienceAction(
                id=a.id,
                kind=a.kind,
                label=a.label,
                status=ActionStatus.ALREADY_COVERED if a.product is not None and a.product in owned
                else ActionStatus.AVAILABLE,
                payload=run_calculator(a.calculator, context.snapshot, a.params, events) if a.calculator else {},
            )
            for a in journey.actions
        ]
        return JourneyCard(
            type=journey.type,
            title=journey.title,
            priority=candidate.score,
            decision_type=candidate.decision_type,
            actions=actions,
        )

    @staticmethod
    def _driving_moment(
        candidate: JourneyCandidate, intents: Sequence[Intent], moments: Sequence[ActiveMoment]
    ) -> ActiveMoment | None:
        """The strongest ACTIVE moment behind the intents that drive this journey."""
        by_type = {i.type: i for i in intents}
        related = {m for t in candidate.driven_by if t in by_type for m in by_type[t].related_moments}
        active = [m for m in moments if m.type in related and m.status == MomentStatus.ACTIVE]
        return max(active, key=lambda m: (m.confidence, m.type.value)) if active else None

    def _why_from_moments(self, moments: Sequence[ActiveMoment]) -> list[WhyItem]:
        evidence = sorted(
            (e for m in moments for e in m.evidence if e.kind == "signal" and e.contribution > 0),
            key=lambda e: -e.contribution,
        )
        items: list[WhyItem] = []
        seen: set[str] = set()
        for e in evidence:
            # Texts come from copy keyed by signal type, so no raw search query can leak.
            text = self.copy.why_by_signal.get(e.ref)  # type: ignore[call-overload]
            if text is None or text in seen:
                continue
            seen.add(text)
            items.append(WhyItem(text=text, contribution=round(e.contribution, 4)))
        return items[:MAX_WHY]

    def _notices(self, cards: Sequence[JourneyCard]) -> list[Notice]:
        notices: list[Notice] = []
        if any(c.decision_type == DecisionType.SHOW_WARNING for c in cards):
            notices.append(Notice(kind="warning", text=self.copy.warning_notice))
        for card in cards:
            for action in card.actions:
                if action.status != ActionStatus.ALREADY_COVERED:
                    continue
                product = self._product_of(card.type, action.id)
                text = self.copy.covered_notice_by_product.get(product, self.copy.covered_notice_default)
                if all(n.text != text for n in notices):
                    notices.append(Notice(kind="reassurance", text=text))
        return notices

    def _product_of(self, journey: JourneyType, action_id: str) -> ProductType | None:
        return next((a.product for a in self.journeys[journey].actions if a.id == action_id), None)

    def _checks(
        self, context: CustomerContext, decision: Decision, cards: Sequence[JourneyCard], owned: set[ProductType]
    ) -> list[CheckItem]:
        c, t, s = self.copy.checks, self.copy.check_thresholds, context.snapshot
        spending = max(s.avg_monthly_spending, 1.0)
        projected = s.projected_balance_before_next_income
        active = [m.type.value for m in context.moments if m.status == MomentStatus.ACTIVE]
        gap = any(
            a.status == ActionStatus.AVAILABLE and self._product_of(card.type, a.id) is not None
            for card in cards for a in card.actions
        )
        protection = sum(1 for p in owned if p in self.copy.protection_products)
        dismissed = sorted({x.journey.value for x in decision.suppressed if x.rule == "FEEDBACK_DISMISSED"})
        return [
            CheckItem(label=c["buffer"], ok=s.emergency_buffer_months >= t.buffer_ok_months,
                      detail=c["buffer_detail"].format(months=s.emergency_buffer_months)),
            CheckItem(label=c["cashflow"],
                      ok=projected >= t.cashflow_ok_abs and projected >= t.cashflow_ok_ratio * spending,
                      detail=c["cashflow_detail"].format(projected=projected)),
            CheckItem(label=c["coverage"], ok=not gap,
                      detail=c["coverage_detail_gap"] if gap else c["coverage_detail_ok"].format(count=protection)),
            CheckItem(label=c["moments"], ok=not active,
                      detail=c["moments_detail_some"].format(moments=", ".join(active)) if active
                      else c["moments_detail_none"]),
            CheckItem(label=c["feedback"], ok=True,
                      detail=c["feedback_detail_some"].format(journeys=", ".join(dismissed)) if dismissed
                      else c["feedback_detail_none"]),
        ]

    @staticmethod
    def _timing(moments: Sequence[ActiveMoment], now: datetime) -> dict[str, str]:
        timing = {"computed_at": now.isoformat()}
        for m in moments:
            timing[f"{m.type.value}_detected_at"] = m.detected_at.isoformat()
            timing[f"{m.type.value}_expires_at"] = m.expires_at.isoformat()
        return timing
