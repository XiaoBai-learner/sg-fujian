from fastapi import APIRouter, Depends, HTTPException
from io import BytesIO
from ...modules.sources.connections.credentials import credential_box, decrypt_password
from ...modules.sources.metadata.mysql import MySQLMetadataReader, MySQLSettings
from ...modules.sources.materials.service import MaterialService
from ...modules.identity.security import current_user
from ..dependencies import get_storage
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
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int = Field(default=3306, ge=1, le=65535)
    username: str | None = Field(default=None, min_length=1, max_length=160)
    password: str | None = Field(default=None, max_length=4096)
    databases: list[str] = Field(default_factory=list, max_length=100)
    source_id: str | None = None


def source_view(source):
    return {'id':source.id,'name':source.name,'kind':source.kind,'database':source.database_name,
            'status':source.last_status,'host':source.host,'port':source.port or 3306,'username':source.username,
            'has_password':bool(source.password_ciphertext),'databases':source.databases_json or ([source.database_name] if source.database_name else [])}


def source_settings(source,storage):
    if not source.host: return MySQLSettings.from_env(source.database_name)
    return MySQLSettings(source.host,source.port or 3306,source.username or '',decrypt_password(storage,source.password_ciphertext) if source.password_ciphertext else '')


def apply_config(source,body,storage):
    if body.kind=='mysql' and body.host and not body.username: raise HTTPException(422,'请填写数据库用户名')
    if any(not name or len(name)>160 or '\x00' in name for name in body.databases): raise HTTPException(422,'数据库名称不合法')
    source.name=body.name.strip()
    if not source.name: raise HTTPException(422,'连接名称不能为空')
    source.host=body.host; source.port=body.port; source.username=body.username
    source.databases_json=list(dict.fromkeys(body.databases))
    source.database_name=(body.databases[0] if body.databases else body.database)
    if body.password is not None: source.password_ciphertext=credential_box(storage).encrypt(body.password.encode()).decode()
    source.last_status='unknown'



class RefreshDDLRequest(BaseModel):
    ddl: str | None = Field(default=None, max_length=10_000_000)


@router.get("")
async def list_sources(session: AsyncSession = Depends(get_session)):
    sources = await SourceService(session).list_connections("local-workspace")
    return {"items": [source_view(source) for source in sources]}


@router.post("", status_code=201)
async def create_source(body: CreateSourceRequest, session: AsyncSession = Depends(get_session), storage=Depends(get_storage)):
    if body.kind=='mysql' and not body.host and not body.database: raise HTTPException(422,'请填写连接主机')
    source = await SourceService(session).create_connection("local-workspace", body.name, body.kind, body.database)
    apply_config(source,body,storage)
    await session.commit()
    return source_view(source)


@router.patch('/{source_id}')
async def update_source(source_id:str,body:CreateSourceRequest,session:AsyncSession=Depends(get_session),storage=Depends(get_storage)):
    source=await session.get(SourceConnectionModel,source_id)
    if source is None or source.workspace_id!='local-workspace': raise HTTPException(404,'连接不存在')
    if source.kind!=body.kind: raise HTTPException(422,'不能修改已有连接类型')
    apply_config(source,body,storage)
    await session.commit()
    return source_view(source)


@router.post('/probe')
async def probe_source(body:CreateSourceRequest,session:AsyncSession=Depends(get_session),storage=Depends(get_storage)):
    if not body.host or not body.username: raise HTTPException(422,'请填写主机与用户名')
    password=body.password or ''
    if body.password is None and body.source_id:
        source=await session.get(SourceConnectionModel,body.source_id)
        if source is None or source.workspace_id!='local-workspace': raise HTTPException(404,'连接不存在')
        password=decrypt_password(storage,source.password_ciphertext) if source.password_ciphertext else ''
    reader=MySQLMetadataReader(MySQLSettings(body.host,body.port,body.username,password))
    try:
        await reader.ping()
        return {'status':'ok','databases':await reader.databases()}
    except Exception as error:
        raise HTTPException(400,detail={'message':'连接失败，请检查主机、端口、凭据和数据库访问权限'}) from error
    finally: await reader.close()


@router.get('/{source_id}/databases')
async def source_databases(source_id:str,session:AsyncSession=Depends(get_session),storage=Depends(get_storage)):
    source=await session.get(SourceConnectionModel,source_id)
    if source is None or source.workspace_id!='local-workspace': raise HTTPException(404,'连接不存在')
    if source.kind!='mysql': raise HTTPException(422,'此操作需要 MySQL 连接')
    reader=MySQLMetadataReader(source_settings(source,storage))
    try: return {'items':await reader.databases()}
    except Exception as error: raise HTTPException(400,'读取数据库失败，请编辑并测试连接') from error
    finally: await reader.close()


@router.post('/{source_id}/materials',status_code=201)
async def collect_material(source_id:str,session:AsyncSession=Depends(get_session),storage=Depends(get_storage),user=Depends(current_user)):
    source=await session.get(SourceConnectionModel,source_id)
    if source is None or source.workspace_id!='local-workspace': raise HTTPException(404,'连接不存在')
    if source.kind!='mysql': raise HTTPException(422,'此操作需要 MySQL 连接')
    reader=MySQLMetadataReader(source_settings(source,storage))
    try: ddl=await reader.export_ddl(source.databases_json or ([source.database_name] if source.database_name else []))
    except Exception as error: raise HTTPException(400,detail={'message':'结构采集失败，请确认所选数据库、权限及结构大小'}) from error
    finally: await reader.close()
    material=await MaterialService(session,storage,2_000_000).create_material('local-workspace',user.id,source.name+'-结构.sql','ddl',BytesIO(ddl.encode()),'text/plain')
    source.last_status='ok'
    await session.commit()
    return {'id':material.material_id,'revision':material.revision,'status':'saved'}



@router.post("/{source_id}/refresh")
async def refresh_source(source_id: str, body: RefreshDDLRequest, session: AsyncSession = Depends(get_session),storage=Depends(get_storage)):
    try:
        source = await session.get(SourceConnectionModel, source_id)
        if source is None:
            raise KeyError("source not found")
        if source.kind == "mysql":
            settings=source_settings(source,storage)
            reader=MySQLMetadataReader(MySQLSettings(settings.host,settings.port,settings.username,settings.password,source.database_name))
            try: tables=await reader.read()
            finally: await reader.close()
            snapshot=await SourceService(session)._persist_snapshot(source,tables)
        elif body.ddl:
            snapshot = await SourceService(session).refresh_ddl(source_id, body.ddl)
        else:
            raise ValueError("ddl is required for ddl source")
    except Exception as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail={"code": "source_refresh_failed", "message": "操作失败，请检查连接配置、所选数据库及读取权限"}) from error
    await session.commit()
    return {"source_id": source_id, "revision": snapshot.revision, "status": snapshot.status}


@router.post("/{source_id}/test")
async def test_source(source_id: str, session: AsyncSession = Depends(get_session), storage=Depends(get_storage)):
    try:
        source=await session.get(SourceConnectionModel,source_id)
        if source is None: raise KeyError('连接不存在')
        if source.kind!='mysql': raise HTTPException(422,'此操作需要 MySQL 连接')
        reader=MySQLMetadataReader(source_settings(source,storage))
        try: await reader.ping()
        finally: await reader.close()
        source.last_status='ok'
        result={'source_id':source_id,'status':'ok'}
    except Exception as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail={"code": "source_test_failed", "message": "操作失败，请检查连接配置、所选数据库及读取权限"}) from error
    await session.commit()
    return result


@router.get("/{source_id}/snapshots/{revision}/tables")
async def list_tables(source_id: str, revision: int, session: AsyncSession = Depends(get_session)):
    try:
        snapshot, tables = await SourceService(session).list_tables(source_id, revision)
    except KeyError as error:
        raise HTTPException(status_code=404, detail={"code": "snapshot_not_found", "message": "操作失败，请检查连接配置、所选数据库及读取权限"}) from error
    return {"source_id": source_id, "revision": snapshot.revision, "items": [
        {"schema": table.schema_name, "name": table.table_name, "comment": table.comment, "primary_key": table.primary_key_json}
        for table in tables
    ]}


@router.get("/{source_id}/snapshots/{revision}/tables/{table_name}/columns")
async def list_columns(source_id: str, revision: int, table_name: str, session: AsyncSession = Depends(get_session)):
    try:
        table, columns = await SourceService(session).list_columns(source_id, revision, table_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail={"code": "table_not_found", "message": "操作失败，请检查连接配置、所选数据库及读取权限"}) from error
    return {"schema": table.schema_name, "table": table.table_name, "items": [
        {"name": column.name, "data_type": column.data_type, "comment": column.comment,
         "nullable": column.nullable, "position": column.position}
        for column in columns
    ]}
