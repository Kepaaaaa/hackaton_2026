"""Demo-only endpoints: scenarios and reset (KBC_DEMO_MODE). Owner: T5."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.customers import MyKbc, to_my_kbc
from app.api.deps import CustomerIdDep, ServiceDep, require_demo_mode
from app.models.common import StrictModel

router = APIRouter(tags=["demo"], dependencies=[Depends(require_demo_mode)])

MAX_STEP = 20

ScenarioId = Annotated[str, Path(pattern=r"^[a-z][a-z0-9_]{1,39}$", description="Scenario id, e.g. `electric_car`.")]
Step = Annotated[int, Path(ge=1, le=MAX_STEP, description="1-based step number.")]


class ScenarioStepOut(StrictModel):
    step: int
    label: str


class ScenarioOut(StrictModel):
    id: str
    title: str
    description: str
    customer_id: str | None
    steps: list[ScenarioStepOut]


@router.get("/scenarios", response_model=list[ScenarioOut], summary="List demo scenarios")
def list_scenarios(service: ServiceDep) -> list[ScenarioOut]:
    return [
        ScenarioOut(
            id=s.id,
            title=s.title,
            description=s.description,
            customer_id=s.customer_id,
            steps=[ScenarioStepOut(step=i, label=st.label) for i, st in enumerate(s.steps, start=1)],
        )
        for s in service.list_scenarios()
    ]


@router.post(
    "/customers/{customer_id}/scenarios/{scenario_id}/steps/{step}",
    response_model=MyKbc,
    summary="Apply one scenario step",
    description="Posts the step's events as live events. Steps are 1-based and can be applied in any order.",
)
def apply_step(
    customer_id: CustomerIdDep, scenario_id: ScenarioId, step: Step, service: ServiceDep
) -> MyKbc:
    return to_my_kbc(service.apply_scenario_step(customer_id, scenario_id, step - 1))


@router.post("/customers/{customer_id}/reset", response_model=MyKbc, summary="Restore the seed state")
def reset(customer_id: CustomerIdDep, service: ServiceDep) -> MyKbc:
    return to_my_kbc(service.reset(customer_id))
