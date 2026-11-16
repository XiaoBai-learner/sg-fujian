from io import BytesIO
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session, get_storage
from ...infrastructure.storage import Storage
from ...modules.sources.materials.models import MaterialModel, MaterialRevisionModel
from ...modules.sources.materials.service import MaterialService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("")
async def list_materials(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(MaterialModel, MaterialRevisionModel).join(
        MaterialRevisionModel, MaterialRevisionModel.material_id == MaterialModel.id,
    ).order_by(MaterialModel.created_at.desc(), MaterialRevisionModel.revision.desc()))).all()
    return {"items": [
        {"id": material.id, "name": material.name, "category": material.category, "revision": revision.revision,
         "parse_status": revision.parse_status, "size_bytes": revision.size_bytes}
        for material, revision in rows
    ]}


@router.post("", status_code=201)
async def upload_material(
    request: Request,
    x_material_name: str = Header(default="material.txt"),
    x_material_category: str = Header(default="document"),
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(get_storage),
):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "material_too_large", "message": "材料超过大小限制"})
    try:
        revision = await MaterialService(session, storage, 20 * 1024 * 1024).create_material(
            "local-workspace",
            "local-user",
            unquote(x_material_name),
            x_material_category,
            BytesIO(await request.body()),
            request.headers.get("content-type", "application/octet-stream"),
        )
    except ValueError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail={"code": "invalid_material", "message": str(error)}) from error
    await session.commit()
    return {"id": revision.material_id, "revision": revision.revision, "parse_status": revision.parse_status}
