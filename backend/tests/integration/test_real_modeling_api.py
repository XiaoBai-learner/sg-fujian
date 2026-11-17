import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sgtrace_app.main import create_app
from sgtrace_app.config import Settings
from sgtrace_app.infrastructure.db.models import Base

DDL="""CREATE TABLE grid.SUBSTATION (ID BIGINT NOT NULL PRIMARY KEY COMMENT '站点标识', NAME VARCHAR(40) COMMENT '站点名称') COMMENT='变电站';
CREATE TABLE grid.READING (ID BIGINT NOT NULL PRIMARY KEY, STATION_ID BIGINT NOT NULL, MW DECIMAL(12,2) COMMENT '有功功率', FOREIGN KEY (STATION_ID) REFERENCES grid.SUBSTATION(ID)) COMMENT='负荷记录';"""
SQL="SELECT s.NAME AS 变电站名称, SUM(r.MW) AS 总功率 FROM grid.SUBSTATION s JOIN grid.READING r ON s.ID = r.STATION_ID GROUP BY s.NAME;"

def client_for(tmp_path):
 settings=Settings(f'sqlite+aiosqlite:///{tmp_path}/app.db',tmp_path/'storage','test',2000000,1,())
 async def init():
  engine=create_async_engine(settings.database_url)
  async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
  await engine.dispose()
 asyncio.run(init())
 return TestClient(create_app(settings))

def upload(client,name,body,category):
 response=client.post('/api/v1/materials',content=body.encode(),headers={'X-Material-Name':name,'X-Material-Category':category})
 assert response.status_code==201,response.text
 return {k:response.json()[k] for k in ('id','revision')}

def test_real_generation_edit_check_adopt_trace_and_reload(tmp_path):
 with client_for(tmp_path) as client:
  refs=[upload(client,'schema.sql',DDL,'ddl'),upload(client,'queries.sql',SQL,'sql')]
  payload={'materials':refs,'request_key':str(uuid4())}
  response=client.post('/api/v1/modeling/runs',json=payload)
  assert response.status_code==201,response.text
  run=response.json(); assert run['status']=='succeeded',run
  assert client.post('/api/v1/modeling/runs',json=payload).json()['id']==run['id']
  assert len(run['result']['draft']['classes'])==2
  assert 'yx186' not in response.text
  before=client.post(f'/api/v1/modeling/runs/{run["id"]}/adopt',json={'revision':1})
  assert before.status_code==409
  check=client.post(f'/api/v1/modeling/runs/{run["id"]}/validate',json={'revision':1})
  assert check.status_code==200,check.text
  assert check.json()['validation']['valid'],check.text
  snap=client.post(f'/api/v1/modeling/runs/{run["id"]}/adopt',json={'revision':1}).json()
  assert snap['id']
  found=client.post('/api/v1/modeling/trace',json={'fields':['变电站名称','总功率','根本不存在']}).json()
  assert found['results'][0]['sources']==['grid.SUBSTATION.NAME'],found
  assert found['results'][1]['sources']==['grid.READING.MW']
  assert found['results'][2]['status']=='not_found'
  cls=run['result']['draft']['classes'][0]
  edit={'revision':1,'type':'edit-class','value':{**cls,'name':'新名称'}}
  changed=client.post(f'/api/v1/modeling/runs/{run["id"]}/draft',json=edit)
  assert changed.status_code==200,changed.text
  assert changed.json()['validation'] is None
  assert client.post(f'/api/v1/modeling/runs/{run["id"]}/draft',json=edit).status_code==409
  assert client.get('/api/v1/modeling/active').json()['id']==snap['id']
  assert client.get(f'/api/v1/modeling/runs/{run["id"]}').json()['revision']==2
  ttl=client.get(f'/api/v1/modeling/snapshots/{snap["id"]}/mapping.ttl')
  assert ttl.status_code==200 and 'TriplesMap' in ttl.text

def test_bad_material_and_missing_key_do_not_claim_adoptable_success(tmp_path):
 with client_for(tmp_path) as client:
  ref=upload(client,'broken.sql','CREATE TABLE X (id','ddl')
  run=client.post('/api/v1/modeling/runs',json={'materials':[ref],'request_key':str(uuid4())}).json()
  assert run['status']=='failed' and run['error']
  ref=upload(client,'nokey.sql',"CREATE TABLE grid.X (v TEXT COMMENT '名称') COMMENT='对象';",'ddl')
  run=client.post('/api/v1/modeling/runs',json={'materials':[ref],'request_key':str(uuid4())}).json()
  check=client.post(f'/api/v1/modeling/runs/{run["id"]}/validate',json={'revision':1}).json()
  assert not check['validation']['valid']
  assert client.post(f'/api/v1/modeling/runs/{run["id"]}/adopt',json={'revision':1}).status_code==422

def test_overlapping_generation_request_keys_share_one_run(tmp_path):
 from sgtrace_app.modules.modeling.service import ModelingService
 from sgtrace_app.infrastructure.db.session import create_session_factory
 from sgtrace_app.infrastructure.storage.local import LocalStorage
 from sgtrace_app.modules.modeling.models import ModelingRun
 from sqlalchemy import select,func
 client=client_for(tmp_path)
 async def concurrent():
  engine=create_async_engine(f'sqlite+aiosqlite:///{tmp_path}/app.db')
  factory=create_session_factory(engine)
  both_ready=asyncio.Event(); arrived=0
  class ConcurrentService(ModelingService):
   async def materials(self,refs):
    nonlocal arrived
    arrived+=1
    if arrived==2: both_ready.set()
    await both_ready.wait()
    return [{'id':'ddl','name':'test.sql','body':DDL,'category':'ddl'}]
  key=str(uuid4())
  async def run():
   async with factory() as session:
    r=await ConcurrentService(session,LocalStorage(tmp_path/'storage')).generate([{'id':'ddl','revision':1}],key)
    return r.id
  results=await asyncio.gather(run(),run())
  assert len(set(results))==1
  async with factory() as session: assert await session.scalar(select(func.count()).select_from(ModelingRun))==1
  await engine.dispose()
 asyncio.run(concurrent())


def test_marketing_trial_inputs_validate_without_changing_active_model(tmp_path):
 from pathlib import Path
 folder=Path(__file__).resolve().parents[3]/'trials/marketing_v1/inputs'
 with client_for(tmp_path) as client:
  refs=[upload(client,path.name,path.read_text(),'ddl' if path.name.startswith('01_') else 'sql')
        for path in sorted(folder.glob('*.sql'))]
  assert len(refs)==4
  response=client.post('/api/v1/modeling/runs',json={'materials':refs,'request_key':str(uuid4()),'semantic':False})
  assert response.status_code==201,response.text
  run=response.json()
  assert run['status']=='succeeded',run.get('error')
  assert run['result']['stats']['tables']==16 and run['result']['stats']['columns']==113
  assert not any(d['code']=='sql_unresolved' for d in run['result']['diagnostics'])
  validation=client.post(f'/api/v1/modeling/runs/{run["id"]}/validate',json={'revision':1})
  assert validation.status_code==200,validation.text
  assert validation.json()['validation']['valid'],validation.text
  assert client.get('/api/v1/modeling/active').json() is None
