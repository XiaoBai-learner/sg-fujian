from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session
from ...infrastructure.db.models import SourceConnectionModel
from ...modules.sources.connections.service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


class CreateSourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(pattern="^(ddl|mysql)$")
    database: str | None = Field(default=None, max_length=160)


class RefreshDDLRequest(BaseModel):
    ddl: str | None = Field(default=None, max_length=10_000_000)


@router.get("")
async def list_sources(session: AsyncSession = Depends(get_session)):
    sources = await SourceService(session).list_connections("local-workspace")
    return {"items": [
        {"id": source.id, "name": source.name, "kind": source.kind,
         "database": source.database_name, "status": source.last_status}
        for source in sources
    ]}


@router.post("", status_code=201)
async def create_source(body: CreateSourceRequest, session: AsyncSession = Depends(get_session)):
    source = await SourceService(session).create_connection("local-workspace", body.name, body.kind, body.database)
    await session.commit()
    return {"id": source.id, "name": source.name, "kind": source.kind, "database": source.database_name, "status": source.last_status}


@router.post("/{source_id}/refresh")
async def refresh_source(source_id: str, body: RefreshDDLRequest, session: AsyncSession = Depends(get_session)):
    try:
        source = await session.get(SourceConnectionModel, source_id)
        if source is None:
            raise KeyError("source not found")
        if source.kind == "mysql":
            snapshot = await SourceService(session).refresh_mysql(source_id)
        elif body.ddl:
            snapshot = await SourceService(session).refresh_ddl(source_id, body.ddl)
        else:
            raise ValueError("ddl is required for ddl source")
    except (KeyError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail={"code": "source_refresh_failed", "message": str(error)}) from error
    await session.commit()
    return {"source_id": source_id, "revision": snapshot.revision, "status": snapshot.status}


@router.post("/{source_id}/test")
async def test_source(source_id: str, session: AsyncSession = Depends(get_session)):
    try:
        result = await SourceService(session).test_mysql(source_id)
    except (KeyError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail={"code": "source_test_failed", "message": str(error)}) from error
    await session.commit()
    return result


@router.get("/{source_id}/snapshots/{revision}/tables")
async def list_tables(source_id: str, revision: int, session: AsyncSession = Depends(get_session)):
    try:
        snapshot, tables = await SourceService(session).list_tables(source_id, revision)
    except KeyError as error:
        raise HTTPException(status_code=404, detail={"code": "snapshot_not_found", "message": str(error)}) from error
    return {"source_id": source_id, "revision": snapshot.revision, "items": [
        {"schema": table.schema_name, "name": table.table_name, "comment": table.comment, "primary_key": table.primary_key_json}
        for table in tables
    ]}


@router.get("/{source_id}/snapshots/{revision}/tables/{table_name}/columns")
async def list_columns(source_id: str, revision: int, table_name: str, session: AsyncSession = Depends(get_session)):
    try:
        table, columns = await SourceService(session).list_columns(source_id, revision, table_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail={"code": "table_not_found", "message": str(error)}) from error
    return {"schema": table.schema_name, "table": table.table_name, "items": [
        {"name": column.name, "data_type": column.data_type, "comment": column.comment,
         "nullable": column.nullable, "position": column.position}
        for column in columns
    ]}
