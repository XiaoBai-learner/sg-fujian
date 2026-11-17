from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_session,get_storage
from ...infrastructure.storage.base import Storage
from ...modules.modeling.service import ModelingService, Conflict, run_view, snapshot_view, WORKSPACE
from ...modules.modeling.models import ModelingRun, AdoptedModel

router=APIRouter(prefix='/modeling',tags=['modeling'])
class MaterialRef(BaseModel):
    id: str=Field(min_length=1,max_length=36)
    revision: int=Field(ge=1)
class Generate(BaseModel):
    materials: list[MaterialRef]=Field(min_length=1,max_length=30)
    request_key: UUID
    semantic: bool=False
class Revision(BaseModel):
    revision: int=Field(ge=1)
class Edit(Revision):
    type: Literal['edit-class','edit-property','edit-relation','exclude']
    value: dict | None=None
    id: str | None=None
    excluded: bool | None=None
class TraceRequest(BaseModel):
    fields: list[str]=Field(min_length=1,max_length=30)
    snapshot_id: str | None=None

def service(session:AsyncSession=Depends(get_session),storage:Storage=Depends(get_storage)):
    return ModelingService(session,storage)

def failure(error):
    return HTTPException(status_code=409 if isinstance(error,Conflict) else 404 if isinstance(error,KeyError) else 422,
                         detail={'code':type(error).__name__,'message':str(error)})

@router.post('/runs',status_code=201)
async def generate(body:Generate,svc=Depends(service)):
    refs=[m.model_dump() for m in body.materials]
    if len({(r['id'],r['revision']) for r in refs})!=len(refs): raise HTTPException(422,'材料不能重复')
    try: return run_view(await svc.generate(refs,str(body.request_key),body.semantic))
    except (ValueError,KeyError) as error: raise failure(error)

@router.get('/runs')
async def list_runs(svc=Depends(service)):
    rows=(await svc.session.scalars(select(ModelingRun).where(ModelingRun.workspace_id==WORKSPACE).order_by(ModelingRun.created_at.desc()).limit(30))).all()
    return {'items':[{'id':r.id,'status':r.status,'revision':r.revision,'created_at':r.created_at} for r in rows]}

@router.get('/runs/{run_id}')
async def get_run(run_id:str,svc=Depends(service)):
    try: return run_view(await svc.get(run_id))
    except KeyError as error: raise failure(error)

@router.post('/runs/{run_id}/draft')
async def edit_run(run_id:str,body:Edit,svc=Depends(service)):
    try: return run_view(await svc.edit(run_id,body.revision,body.model_dump(exclude={'revision'})))
    except (ValueError,KeyError) as error: raise failure(error)

@router.post('/runs/{run_id}/validate')
async def validate(run_id:str,body:Revision,svc=Depends(service)):
    try: return run_view(await svc.validate(run_id,body.revision))
    except (ValueError,KeyError) as error: raise failure(error)

@router.post('/runs/{run_id}/adopt')
async def adopt(run_id:str,body:Revision,svc=Depends(service)):
    try: return snapshot_view(await svc.adopt(run_id,body.revision))
    except (ValueError,KeyError) as error: raise failure(error)

@router.get('/active')
async def active(svc=Depends(service)): return snapshot_view(await svc.active())

@router.post('/trace')
async def trace_fields(body:TraceRequest,svc=Depends(service)):
    if any(not f.strip() or len(f)>200 for f in body.fields): raise HTTPException(422,'字段名不能为空或超过 200 字符')
    try: return await svc.trace(body.fields,body.snapshot_id)
    except ValueError as error: raise failure(error)

@router.get('/snapshots/{snapshot_id}/{artifact}')
async def download(snapshot_id:str,artifact:Literal['ontology.ttl','mapping.ttl'],svc=Depends(service)):
    snapshot=await svc.session.scalar(select(AdoptedModel).where(AdoptedModel.id==snapshot_id,AdoptedModel.workspace_id==WORKSPACE))
    if snapshot is None: raise HTTPException(404,'模型快照不存在')
    return Response(snapshot.artifacts_json[artifact],media_type='text/turtle',headers={'Content-Disposition':f'attachment; filename="{artifact}"'})
