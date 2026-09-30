"""Events: facts about a customer (A.7). Owner: T0.

Two discriminated unions on `type`:
- `CustomerEvent`: stored events (server-set id, customer_id, timestamp, origin).
- `EventInput`: API input, same payloads without server fields, plus a bounded
  demo-only `days_ago`. Convert with `event_input_to_event` (or `.to_event` on
  any input instance).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, ClassVar, Literal, Union

from pydantic import AwareDatetime, Field, StringConstraints, TypeAdapter, field_validator

from app.models.common import (
    CustomerId,
    EventType,
    FeedbackType,
    JourneyType,
    KbcPage,
    LifeEventDeclared,
    ProductType,
    SimulationType,
    StrictModel,
    TransactionCategory,
    reject_control_chars,
    round_money,
)

# --- Payloads -----------------------------------------------------------------


class TransactionData(StrictModel):
    direction: Literal["in", "out"]
    amount: float = Field(gt=0, le=1_000_000)
    currency: Literal["EUR"] = "EUR"
    category: TransactionCategory
    merchant: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    account_id: Annotated[str, StringConstraints(max_length=64)] | None = None
    recurring: bool = False

    @field_validator("amount")
    @classmethod
    def _round_amount(cls, v: float) -> float:
        return round_money(v)

    @field_validator("merchant")
    @classmethod
    def _clean_merchant(cls, v: str) -> str:
        return reject_control_chars(v)

    def signed_amount(self) -> float:
        return self.amount if self.direction == "in" else -self.amount


class PageViewData(StrictModel):
    page: KbcPage


class SimulationData(StrictModel):
    simulation_type: SimulationType
    amount: float | None = Field(None, gt=0, le=5_000_000)
    duration_months: int | None = Field(None, ge=1, le=480)


class KbcSearchData(StrictModel):
    # Stripped, control chars rejected, max 100 chars. Never echo this into logs or descriptions.
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

    @field_validator("query")
    @classmethod
    def _clean_query(cls, v: str) -> str:
        return reject_control_chars(v)


class ProductOpenedData(StrictModel):
    product: ProductType


class DeclaredLifeEventData(StrictModel):
    life_event: LifeEventDeclared


class FeedbackData(StrictModel):
    journey: JourneyType
    feedback: FeedbackType


class JourneyInteractionData(StrictModel):
    journey: JourneyType
    action_id: str = Field(max_length=64, pattern=r"^[A-Z0-9_]+$")


# --- Stored events --------------------------------------------------------------


class _EventBase(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    customer_id: CustomerId
    timestamp: AwareDatetime
    origin: Literal["seed", "live"]  # live = posted through the API after seed


class TransactionEvent(_EventBase):
    type: Literal[EventType.TRANSACTION] = EventType.TRANSACTION
    data: TransactionData


class PageViewEvent(_EventBase):
    type: Literal[EventType.PAGE_VIEW] = EventType.PAGE_VIEW
    data: PageViewData


class SimulationEvent(_EventBase):
    type: Literal[EventType.SIMULATION] = EventType.SIMULATION
    data: SimulationData


class KbcSearchEvent(_EventBase):
    type: Literal[EventType.KBC_SEARCH] = EventType.KBC_SEARCH
    data: KbcSearchData


class ProductOpenedEvent(_EventBase):
    type: Literal[EventType.PRODUCT_OPENED] = EventType.PRODUCT_OPENED
    data: ProductOpenedData


class DeclaredLifeEvent(_EventBase):
    type: Literal[EventType.DECLARED_LIFE_EVENT] = EventType.DECLARED_LIFE_EVENT
    data: DeclaredLifeEventData


class RecommendationFeedbackEvent(_EventBase):
    type: Literal[EventType.RECOMMENDATION_FEEDBACK] = EventType.RECOMMENDATION_FEEDBACK
    data: FeedbackData


class JourneyInteractionEvent(_EventBase):
    type: Literal[EventType.JOURNEY_INTERACTION] = EventType.JOURNEY_INTERACTION
    data: JourneyInteractionData


CustomerEvent = Annotated[
    Union[
        TransactionEvent,
        PageViewEvent,
        SimulationEvent,
        KbcSearchEvent,
        ProductOpenedEvent,
        DeclaredLifeEvent,
        RecommendationFeedbackEvent,
        JourneyInteractionEvent,
    ],
    Field(discriminator="type"),
]
CustomerEventAdapter: TypeAdapter[CustomerEvent] = TypeAdapter(CustomerEvent)


# --- API input --------------------------------------------------------------------


class _EventInputBase(StrictModel):
    days_ago: int = Field(0, ge=0, le=365)  # demo time travel only, bounded

    event_class: ClassVar[type[_EventBase]]

    def to_event(self, customer_id: str, now: datetime, id: str) -> CustomerEvent:
        """Build the stored event. The server sets id, timestamp and origin="live"."""
        return self.event_class(
            id=id,
            customer_id=customer_id,
            timestamp=now - timedelta(days=self.days_ago),
            origin="live",
            data=self.data,  # type: ignore[attr-defined]
        )


class TransactionInput(_EventInputBase):
    event_class: ClassVar = TransactionEvent
    type: Literal[EventType.TRANSACTION] = EventType.TRANSACTION
    data: TransactionData


class PageViewInput(_EventInputBase):
    event_class: ClassVar = PageViewEvent
    type: Literal[EventType.PAGE_VIEW] = EventType.PAGE_VIEW
    data: PageViewData


class SimulationInput(_EventInputBase):
    event_class: ClassVar = SimulationEvent
    type: Literal[EventType.SIMULATION] = EventType.SIMULATION
    data: SimulationData


class KbcSearchInput(_EventInputBase):
    event_class: ClassVar = KbcSearchEvent
    type: Literal[EventType.KBC_SEARCH] = EventType.KBC_SEARCH
    data: KbcSearchData


class ProductOpenedInput(_EventInputBase):
    event_class: ClassVar = ProductOpenedEvent
    type: Literal[EventType.PRODUCT_OPENED] = EventType.PRODUCT_OPENED
    data: ProductOpenedData


class DeclaredLifeEventInput(_EventInputBase):
    event_class: ClassVar = DeclaredLifeEvent
    type: Literal[EventType.DECLARED_LIFE_EVENT] = EventType.DECLARED_LIFE_EVENT
    data: DeclaredLifeEventData


class RecommendationFeedbackInput(_EventInputBase):
    event_class: ClassVar = RecommendationFeedbackEvent
    type: Literal[EventType.RECOMMENDATION_FEEDBACK] = EventType.RECOMMENDATION_FEEDBACK
    data: FeedbackData


class JourneyInteractionInput(_EventInputBase):
    event_class: ClassVar = JourneyInteractionEvent
    type: Literal[EventType.JOURNEY_INTERACTION] = EventType.JOURNEY_INTERACTION
    data: JourneyInteractionData


EventInput = Annotated[
    Union[
        TransactionInput,
        PageViewInput,
        SimulationInput,
        KbcSearchInput,
        ProductOpenedInput,
        DeclaredLifeEventInput,
        RecommendationFeedbackInput,
        JourneyInteractionInput,
    ],
    Field(discriminator="type"),
]
EventInputAdapter: TypeAdapter[EventInput] = TypeAdapter(EventInput)


def event_input_to_event(event_input: EventInput, customer_id: str, now: datetime, id: str) -> CustomerEvent:
    return event_input.to_event(customer_id, now, id)
