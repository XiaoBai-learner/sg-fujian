"""Assemble the only supported business API version."""
from fastapi import APIRouter, Depends

from ...modules.agent import router as agent
from ...modules.modeling import router as modeling
from ...modules.sources import router as sources
from .sources import router as source_endpoints
from .materials import router as material_endpoints
from .modeling import router as modeling_endpoints
from .auth import router as auth_endpoints, accounts
from ...modules.identity.security import current_user

router = APIRouter(prefix="/api/v1")
router.include_router(auth_endpoints)
router.include_router(accounts)
for business in (sources, source_endpoints, material_endpoints, modeling, modeling_endpoints, agent):
    router.include_router(business, dependencies=[Depends(current_user)])
