"""Customer and persistent profile (A.7). Owner: T0.

`age` is display only: no rule may use it (see rules/schema.py ProfileAdjustment).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from app.models.common import CustomerId, ProductType, StrictModel


class Employment(StrictModel):
    status: Literal["employed", "self_employed", "unemployed", "retired", "student"]
    type: Literal["salaried", "freelance", "none"]


class Housing(StrictModel):
    status: Literal["tenant", "homeowner", "living_with_parents"]
    mortgage: bool


class Family(StrictModel):
    status: Literal["single", "partner", "married"]
    children: int = Field(ge=0, le=20)


class FinancialProfile(StrictModel):
    savings_level: Literal["low", "medium", "high"]
    income_stability: Literal["stable", "variable", "none"]
    financial_maturity: Literal["beginner", "intermediate", "experienced"]


class CustomerProfile(StrictModel):
    """Composable persistent attributes, NOT a segment."""

    life_stage: Literal[
        "student", "young_professional", "established", "family", "pre_retirement", "retired"
    ]
    employment: Employment
    income_stage: Literal["none", "first_recurring_salary", "established", "pension"]
    housing: Housing
    family: Family
    financial_profile: FinancialProfile


class Consent(StrictModel):
    personalization: bool = True


class Account(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    type: Literal["current", "savings", "child_savings", "pension_savings", "investment"]
    label: str = Field(min_length=1, max_length=80)
    masked_number: str = Field(max_length=32)  # "•••• 4821", fake
    balance: float  # balance at seed time
    currency: Literal["EUR"] = "EUR"


class OwnedProduct(StrictModel):
    product: ProductType
    since: date
    details: dict[str, str | float | bool] = {}


class Customer(StrictModel):
    id: CustomerId
    first_name: str = Field(min_length=1, max_length=40)
    age: int = Field(ge=0, le=130)  # display only, never a rule input
    profile: CustomerProfile
    accounts: list[Account]
    products: list[OwnedProduct]
    consent: Consent = Consent()

    def owned_products(self) -> list[ProductType]:
        return [p.product for p in self.products]
