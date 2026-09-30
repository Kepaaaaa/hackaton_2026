"""FastAPI dependencies. Owner: T5.

`resolve_customer` is the single choke point for customer ids (A.10). In this PoC the id
comes from the path; in production it would come from the authenticated session, and this
function is the only place to change.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, Path, Request

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.services.personalization_service import PersonalizationService

_CUSTOMER_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")


def get_service(request: Request) -> PersonalizationService:
    return request.app.state.service


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


ServiceDep = Annotated[PersonalizationService, Depends(get_service)]


def resolve_customer(
    service: ServiceDep,
    customer_id: Annotated[str, Path(description="Customer id, e.g. `lucas`.")],
) -> str:
    """Validate the id and check it exists. Invalid and unknown ids get the same neutral 404."""
    if not _CUSTOMER_ID_RE.fullmatch(customer_id):
        raise NotFoundError()
    service.get_customer(customer_id)
    return customer_id


CustomerIdDep = Annotated[str, Depends(resolve_customer)]


def require_demo_mode(settings: Annotated[Settings, Depends(get_app_settings)]) -> None:
    """Demo endpoints do not exist when KBC_DEMO_MODE=false (404, not 403, to hide them)."""
    if not settings.demo_mode:
        raise NotFoundError()
