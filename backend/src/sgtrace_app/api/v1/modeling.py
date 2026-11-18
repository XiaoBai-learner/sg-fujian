from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_session,get_storage
from ...infrastructure.storage.base import Storage
from ...modules.modeling.service import ModelingService, Conflict, run_view, snapshot_view, WORKSPACE
from ...modules.modeling.models import ModelingRun, AdoptedModel, OntologyModel
from ...modules.agent.models import TraceAttachment
from fastapi import Request
from io import BytesIO
from uuid import uuid4

router=APIRouter(prefix='/modeling',tags=['modeling'])
class MaterialRef(BaseModel):
    id: str=Field(min_length=1,max_length=36)
    revision: int=Field(ge=1)
class Generate(BaseModel):
    materials: list[MaterialRef]=Field(min_length=1,max_length=30)
    request_key: UUID
    semantic: bool=False
    model_id: str | None=None
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
    attachment_ids: list[str]=Field(default_factory=list,max_length=5)

def service(session:AsyncSession=Depends(get_session),storage:Storage=Depends(get_storage)):
    return ModelingService(session,storage)

def failure(error):
    return HTTPException(status_code=409 if isinstance(error,Conflict) else 404 if isinstance(error,KeyError) else 422,
                         detail={'code':type(error).__name__,'message':str(error)})


class ModelInput(BaseModel):
    name: str=Field(min_length=1,max_length=160)
    group: str=Field(default='未分组',min_length=1,max_length=160)

class BusinessContext(BaseModel):
    text: str=Field(max_length=10000)

def model_summary(model,run=None):
    draft=run.result_json.get('draft',{}) if run and run.result_json else {}
    return {'id':model.id,'name':model.name,'group':model.group_name,'run_id':model.current_run_id,
            'adopted_id':model.adopted_id,'created_at':model.created_at,
            'class_count':len(draft.get('classes',[])),'relation_count':len(draft.get('relations',[]))}

@router.get('/models')
async def list_models(svc=Depends(service)):
    rows=(await svc.session.execute(select(OntologyModel,ModelingRun).outerjoin(ModelingRun,ModelingRun.id==OntologyModel.current_run_id).where(
        OntologyModel.workspace_id==WORKSPACE).order_by(OntologyModel.created_at.desc()))).all()
    return {'items':[model_summary(model,run) for model,run in rows]}

@router.post('/models',status_code=201)
async def create_model(body:ModelInput,svc=Depends(service)):
    if not body.name.strip() or not body.group.strip(): raise HTTPException(422,'名称和分组不能为空')
    model=OntologyModel(workspace_id=WORKSPACE,name=body.name.strip(),group_name=body.group.strip())
    svc.session.add(model); await svc.session.commit(); await svc.session.refresh(model)
    return model_summary(model)

@router.patch('/models/{model_id}')
async def rename_model(model_id:str,body:ModelInput,svc=Depends(service)):
    try: model=await svc.model(model_id)
    except KeyError as error: raise failure(error)
    if not body.name.strip() or not body.group.strip(): raise HTTPException(422,'名称和分组不能为空')
    model.name=body.name.strip(); model.group_name=body.group.strip()
    await svc.session.commit()
    return model_summary(model)

@router.get('/models/{model_id}')
async def get_model(model_id:str,svc=Depends(service)):
    try: model=await svc.model(model_id)
    except KeyError as error: raise failure(error)
    run=await svc.get(model.current_run_id) if model.current_run_id else None
    adopted=await svc.session.get(AdoptedModel,model.adopted_id) if model.adopted_id else None
    return {**model_summary(model,run),'business_context':model.business_context or '', 'run':run_view(run) if run else None,'active':snapshot_view(adopted)}

@router.post('/models/{model_id}/context')
async def save_context(model_id:str,body:BusinessContext,svc=Depends(service)):
    try: model=await svc.model(model_id)
    except KeyError as error: raise failure(error)
    if '\x00' in body.text: raise HTTPException(422,'业务流程不能包含空字符')
    model.business_context=body.text.strip()
    await svc.session.commit()
    return {'business_context':model.business_context}

@router.post('/attachments',status_code=201)
async def upload_attachment(request:Request,svc=Depends(service)):
    content_type=request.headers.get('content-type','')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>5_000_000: raise HTTPException(413,'截图最多 5 MB')
    valid=(content_type=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (content_type=='image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (content_type=='image/webp' and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP')
    if not valid: raise HTTPException(422,'请上传 PNG、JPEG 或 WebP 截图')
    stored=svc.storage.put(BytesIO(raw),'trace/'+str(uuid4()),content_type,5_000_000)
    attachment=TraceAttachment(workspace_id=WORKSPACE,content_uri=stored.uri,content_type=content_type,size_bytes=len(raw))
    svc.session.add(attachment); await svc.session.commit()
    return {'id':attachment.id,'url':f'/api/v1/modeling/attachments/{attachment.id}','ocr_status':'not_configured'}

@router.get('/attachments/{attachment_id}')
async def read_attachment(attachment_id:str,svc=Depends(service)):
    item=await svc.session.get(TraceAttachment,attachment_id)
    if item is None or item.workspace_id!=WORKSPACE: raise HTTPException(404,'截图不存在')
    with svc.storage.open(item.content_uri) as stream: raw=stream.read(5_000_001)
    return Response(raw,media_type=item.content_type)

@router.post('/runs',status_code=201)
async def generate(body:Generate,svc=Depends(service)):
    refs=[m.model_dump() for m in body.materials]
    if len({(r['id'],r['revision']) for r in refs})!=len(refs): raise HTTPException(422,'材料不能重复')
    try: return run_view(await svc.generate(refs,str(body.request_key),body.semantic,body.model_id))
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
    for attachment_id in body.attachment_ids:
        item=await svc.session.get(TraceAttachment,attachment_id)
        if item is None or item.workspace_id!=WORKSPACE: raise HTTPException(422,'截图不存在')
    try:
        result=await svc.trace(body.fields,body.snapshot_id)
        result['attachment_ids']=body.attachment_ids
        result['screenshot_analysis']='not_configured' if body.attachment_ids else 'not_requested'
        return result
    except ValueError as error: raise failure(error)

@router.get('/snapshots/{snapshot_id}/{artifact}')
async def download(snapshot_id:str,artifact:Literal['ontology.ttl','mapping.ttl'],svc=Depends(service)):
    snapshot=await svc.session.scalar(select(AdoptedModel).where(AdoptedModel.id==snapshot_id,AdoptedModel.workspace_id==WORKSPACE))
    if snapshot is None: raise HTTPException(404,'模型快照不存在')
    return Response(snapshot.artifacts_json[artifact],media_type='text/turtle',headers={'Content-Disposition':f'attachment; filename="{artifact}"'})
