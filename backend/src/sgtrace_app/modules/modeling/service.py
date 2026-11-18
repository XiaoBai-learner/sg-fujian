"""Persistent material-bound modeling, optimistic edits and immutable snapshots."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ...infrastructure.storage.base import Storage
from ...integrations.ontowing.adapter import compile_model
from ..sources.materials.models import MaterialModel, MaterialRevisionModel
from .runner import analyze
from .semantic_index import trace, source_index
from .models import ModelingRun, AdoptedModel, OntologyModel

WORKSPACE='local-workspace'

class Conflict(ValueError): pass

class TextEdit(BaseModel):
    model_config=ConfigDict(extra='ignore')
    id: str
    name: str=Field(min_length=1,max_length=160)
    description: str=Field(max_length=2000)

class ClassEdit(TextEdit):
    aliases: list[str]=Field(max_length=30)
    parentId: str | None

class PropertyEdit(TextEdit):
    aliases: list[str]=Field(max_length=30)
    conceptId: str | None
    datatype: str
    unit: str=Field(max_length=40)

class RelationEdit(TextEdit):
    sourceId: str
    targetId: str
    cardinality: str
    symmetric: bool
    transitive: bool
    functional: bool


def digest(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def edit_draft(draft, action):
    draft=deepcopy(draft)
    kind=action['type']
    if kind=='exclude':
        item=next((i for i in draft['items'] if i['id']==action.get('id')),None)
        if item is None or type(action.get('excluded')) is not bool: raise ValueError('无效字段选择')
        item['excluded']=action['excluded']
    else:
        spec,group={'edit-class':(ClassEdit,'classes'),'edit-property':(PropertyEdit,'items'),'edit-relation':(RelationEdit,'relations')}[kind]
        try: value=spec.model_validate(action.get('value')).model_dump()
        except ValidationError as error: raise ValueError('编辑字段不合法') from error
        value['name']=value['name'].strip()
        if not value['name'] or any(ord(c)<32 for c in value['name']): raise ValueError('名称不能为空或包含控制字符')
        if 'aliases' in value:
            if any(not a.strip() or len(a)>160 for a in value['aliases']): raise ValueError('同义叫法不合法')
            value['aliases']=sorted(set(a.strip() for a in value['aliases']))
        target=next((i for i in draft[group] if i['id']==value['id']),None)
        if target is None: raise ValueError('编辑对象不存在')
        target.update(value); target['edited']=True
    classes={c['id']:c for c in draft['classes']}
    if len({c['name'] for c in draft['classes']})!=len(classes): raise ValueError('类名称重复')
    for c in classes.values():
        seen={c['id']}; parent=c['parentId']
        while parent:
            if parent not in classes or parent in seen: raise ValueError('父类引用不存在或存在循环')
            seen.add(parent); parent=classes[parent]['parentId']
    slots=set()
    for item in draft['items']:
        cid=item['conceptId']
        if cid is not None and cid not in classes or cid is None and not item.get('uncertain'): raise ValueError('属性所属类不存在')
        if item['datatype'] not in {'string','integer','decimal','boolean','date','datetime'}: raise ValueError('属性类型无效')
        slot=(cid,item['name'])
        if slot in slots: raise ValueError('同一类不能有重名属性')
        slots.add(slot)
        if cid: item['concept']=classes[cid]['name']
    for relation in draft['relations']:
        if relation['sourceId'] not in classes or relation['targetId'] not in classes: raise ValueError('关系端点不存在')
        if relation['cardinality'] not in {'unknown','one-to-one','one-to-many','many-to-one','many-to-many'}: raise ValueError('关系基数无效')
    draft['revision']+=1
    return draft

class ModelingService:
    def __init__(self,session:AsyncSession,storage:Storage): self.session,self.storage=session,storage

    async def materials(self,references):
        result=[]; total=0
        for ref in sorted(references,key=lambda x:(x['id'],x['revision'])):
            row=(await self.session.execute(select(MaterialModel,MaterialRevisionModel).join(MaterialRevisionModel,MaterialRevisionModel.material_id==MaterialModel.id).where(
                MaterialModel.id==ref['id'],MaterialModel.workspace_id==WORKSPACE,MaterialRevisionModel.revision==ref['revision']))).first()
            if row is None: raise ValueError('材料版本不存在或不属于当前工作区')
            material,revision=row
            if Path(material.name).suffix.lower() not in {'.sql','.txt','.md'}: raise ValueError(material.name+' 尚不支持自动解析，请先提供 UTF-8 正文')
            with self.storage.open(revision.content_uri) as stream: raw=stream.read(2_000_001)
            total+=len(raw)
            if len(raw)>2_000_000 or total>5_000_000: raise ValueError('单份正文最多 2 MB，总正文最多 5 MB')
            if sha256(raw).hexdigest()!=revision.source_sha256: raise ValueError('材料完整性校验失败')
            result.append({'id':material.id,'name':material.name,'revision':revision.revision,'body':raw.decode('utf-8'),
                           'category':material.category,'sha256':revision.source_sha256,'size':len(raw)})
        return result

    async def generate(self,refs,key,semantic=False,model_id=None):
        model=await self.model(model_id) if model_id else None
        context=(model.business_context or '') if model else ''
        fingerprint=digest({'materials':sorted(refs,key=lambda r:r['id']),'semantic':semantic,'method':'schema-sql-evidence/1',**({'model_id':model_id} if model_id else {}),**({'business_context':context} if context else {})})
        prior=await self.session.scalar(select(ModelingRun).where(ModelingRun.request_key==key,ModelingRun.workspace_id==WORKSPACE))
        if prior:
            if prior.input_sha256!=fingerprint: raise Conflict('同一请求标识不能用于不同材料')
            return prior
        material_inputs=await self.materials(refs)
        if context:
            if len(material_inputs)>=30: raise ValueError('补充业务流程时，最多选择 29 份文档材料')
            raw=context.encode('utf-8')
            material_inputs.append({'id':'context-'+model.id[:24], 'revision':1,
                                   'name':'业务流程说明.md','body':context,'category':'document',
                                   'source_kind':'model_context','sha256':sha256(raw).hexdigest(),'size':len(raw)})
        if model is None:
            model=OntologyModel(id=str(uuid4()),workspace_id=WORKSPACE,name='材料模型 '+key[:8],group_name='未分组')
            self.session.add(model)
            model_id=model.id
        run=ModelingRun(id=str(uuid4()),workspace_id=WORKSPACE,request_key=key,input_sha256=fingerprint,status='running',revision=1,
                        input_json={'materials':refs,'semantic':semantic,**({'business_context':context} if context else {})},model_id=model_id)
        self.session.add(run)
        try: await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            prior=await self.session.scalar(select(ModelingRun).where(ModelingRun.request_key==key,ModelingRun.workspace_id==WORKSPACE))
            if prior is None: raise
            if prior.input_sha256!=fingerprint: raise Conflict('同一请求标识不能用于不同材料')
            return prior
        try:
            result=await run_in_threadpool(analyze,material_inputs,semantic)
            result['materials']=material_inputs
            run.result_json=result; run.status='succeeded'
            if model:
                # A new generation is a separate version; no existing draft is overwritten.
                model.current_run_id=run.id
            for ref in refs:
                await self.session.execute(update(MaterialRevisionModel).where(MaterialRevisionModel.material_id==ref['id'],MaterialRevisionModel.revision==ref['revision']).values(parse_status='succeeded',parse_error=None))
        except ValueError as error:
            run.status='failed'; run.error=str(error)[:500]
        except Exception:
            run.status='failed'; run.error='建模依赖异常，本轮未生成可用模型。'
        await self.session.commit()
        return run

    async def get(self,run_id):
        run=await self.session.scalar(select(ModelingRun).where(ModelingRun.id==run_id,ModelingRun.workspace_id==WORKSPACE))
        if run is None: raise KeyError('建模记录不存在')
        return run

    async def edit(self,run_id,revision,action):
        run=await self.get(run_id)
        if run.status!='succeeded' or not run.result_json: raise ValueError('当前任务没有可编辑结果')
        if run.revision!=revision: raise Conflict('草稿已变化，请重新读取')
        result=deepcopy(run.result_json); result['draft']=edit_draft(result['draft'],action)
        changed=await self.session.execute(update(ModelingRun).where(ModelingRun.id==run.id,ModelingRun.revision==revision).values(
            result_json=result,revision=revision+1,validation_json=None))
        if changed.rowcount!=1: await self.session.rollback(); raise Conflict('草稿已变化，请重新读取')
        await self.session.commit(); await self.session.refresh(run)
        return run

    async def validate(self,run_id,revision):
        run=await self.get(run_id)
        if run.revision!=revision: raise Conflict('草稿已变化，请重新检查')
        if not run.result_json: raise ValueError('无可用草稿')
        result=deepcopy(run.result_json)
        compiled=await run_in_threadpool(compile_model,result['draft'],result['tables'])
        report={**compiled,'revision':revision,'draft_sha256':digest(result['draft'])}
        if compiled['valid']:
            _,index=source_index({**compiled['artifacts'],'pipeline':compiled['pipeline']})
            bound={s for sources in index.values() for s in sources}
            missing=[i['name'] for i in result['draft']['items'] if not i.get('excluded') and not i.get('uncertain') and not set(i['sources'])<=bound]
            if missing:
                report['valid']=False; report['problems'].append({'code':'unbound_dependency','message':'未映射的计算依赖：'+ '、'.join(missing)})
        changed=await self.session.execute(update(ModelingRun).where(ModelingRun.id==run.id,ModelingRun.revision==revision).values(validation_json=report))
        if changed.rowcount!=1: await self.session.rollback(); raise Conflict('检查期间草稿变化，请重新检查')
        await self.session.commit(); await self.session.refresh(run)
        return run

    async def adopt(self,run_id,revision):
        run=await self.session.scalar(select(ModelingRun).where(ModelingRun.id==run_id,ModelingRun.workspace_id==WORKSPACE).with_for_update())
        if run is None: raise KeyError('建模记录不存在')
        check=run.validation_json
        if run.revision!=revision or not check or check['revision']!=revision or check['draft_sha256']!=digest(run.result_json['draft']): raise Conflict('请检查当前草稿后再采用')
        if not check['valid']: raise ValueError('模型校验未通过，不可采用')
        old=await self.session.scalar(select(AdoptedModel).where(AdoptedModel.run_id==run.id,AdoptedModel.revision==revision))
        if old: return old
        draft=run.result_json['draft']
        snapshot={'items':[i for i in draft['items'] if not i.get('excluded') and not i.get('uncertain')],
                  'classes':draft['classes'],'relations':[r for r in draft['relations'] if not r.get('uncertain')]}
        artifacts={**check['artifacts'],'pipeline':check['pipeline']}
        adopted=AdoptedModel(workspace_id=WORKSPACE,run_id=run.id,revision=revision,snapshot_json=snapshot,artifacts_json=artifacts,created_at=datetime.now(timezone.utc))
        self.session.add(adopted); await self.session.flush()
        if run.model_id:
            model=await self.model(run.model_id)
            model.adopted_id=adopted.id
        await self.session.commit(); await self.session.refresh(adopted)
        return adopted

    async def model(self, model_id):
        model=await self.session.scalar(select(OntologyModel).where(OntologyModel.id==model_id,OntologyModel.workspace_id==WORKSPACE))
        if model is None: raise KeyError('本体模型不存在')
        return model

    async def active(self):
        return await self.session.scalar(select(AdoptedModel).where(AdoptedModel.workspace_id==WORKSPACE).order_by(AdoptedModel.created_at.desc(),AdoptedModel.id.desc()).limit(1))

    async def trace(self,fields,snapshot_id=None):
        snapshot=await self.session.scalar(select(AdoptedModel).where(AdoptedModel.id==snapshot_id,AdoptedModel.workspace_id==WORKSPACE)) if snapshot_id else await self.active()
        if not snapshot: raise ValueError('尚无已采用模型')
        return {'snapshot_id':snapshot.id,'version':snapshot.revision,'run_id':snapshot.run_id,
                'results':[trace(snapshot.artifacts_json,snapshot.snapshot_json,field) for field in fields]}


def run_view(run):
    return {'id':run.id,'model_id':run.model_id,'status':run.status,'revision':run.revision,'result':run.result_json,'validation':run.validation_json,'error':run.error}

def snapshot_view(snapshot):
    return None if snapshot is None else {'id':snapshot.id,'run_id':snapshot.run_id,'version':snapshot.revision,**snapshot.snapshot_json}
