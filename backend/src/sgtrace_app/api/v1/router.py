"""Assemble the only supported business API version."""
from fastapi import APIRouter

from ...modules.agent import router as agent
from ...modules.modeling import router as modeling
from ...modules.sources import router as sources
from .sources import router as source_endpoints
from .materials import router as material_endpoints

router = APIRouter(prefix="/api/v1")
router.include_router(sources)
router.include_router(source_endpoints)
router.include_router(material_endpoints)
router.include_router(modeling)
router.include_router(agent)
