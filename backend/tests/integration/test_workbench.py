"""Workbench operations persist facts; no browser-only connection or model state."""
from uuid import uuid4
import os
import pytest

from test_real_modeling_api import client_for, upload, DDL


def test_named_models_keep_independent_drafts_and_adopted_versions(tmp_path):
    with client_for(tmp_path) as client:
        first = client.post('/api/v1/modeling/models', json={'name': '客户模型', 'group': '营销基础'})
        assert first.status_code == 201, first.text
        first_id = first.json()['id']
        second = client.post('/api/v1/modeling/models', json={'name': '计量模型', 'group': '营销基础'}).json()
        ref = upload(client, 'schema.sql', DDL, 'ddl')
        run = client.post('/api/v1/modeling/runs', json={
            'materials': [ref], 'request_key': str(uuid4()), 'model_id': first_id,
        }).json()
        assert run['model_id'] == first_id
        assert run['status'] == 'succeeded'
        detail = client.get(f'/api/v1/modeling/models/{first_id}').json()
        assert detail['run']['id'] == run['id']
        assert client.get(f'/api/v1/modeling/models/{second["id"]}').json()['run'] is None
        renamed = client.patch(f'/api/v1/modeling/models/{first_id}', json={'name': '客户资产', 'group': '基础数据'})
        assert renamed.status_code == 200
        listing = client.get('/api/v1/modeling/models').json()['items']
        assert {m['name'] for m in listing} == {'客户资产', '计量模型'}
        assert next(m for m in listing if m['id'] == first_id)['class_count'] == 2
        check = client.post(f'/api/v1/modeling/runs/{run["id"]}/validate', json={'revision': 1})
        assert check.json()['validation']['valid'], check.text
        snap = client.post(f'/api/v1/modeling/runs/{run["id"]}/adopt', json={'revision': 1}).json()
        assert client.get(f'/api/v1/modeling/models/{first_id}').json()['active']['id'] == snap['id']
        assert client.get(f'/api/v1/modeling/models/{second["id"]}').json()['active'] is None
        found = client.post('/api/v1/modeling/trace', json={'snapshot_id': snap['id'], 'fields': ['站点名称', '不存在的字段']}).json()['results']
        assert 0 < found[0]['confidence'] < 1
        assert found[0]['confidence_basis']
        assert found[1]['confidence'] is None
        assert found[1]['status'] == 'not_found'
        bad = client.post('/api/v1/modeling/runs', json={'materials': [ref], 'request_key': str(uuid4()), 'model_id': str(uuid4())})
        assert bad.status_code == 404


def test_connection_configuration_edit_and_password_redaction(tmp_path):
    with client_for(tmp_path) as client:
        payload = {'name': '本机业务库', 'kind': 'mysql', 'host': '127.0.0.1', 'port': 3306,
                   'username': 'metadata_reader', 'password': 'private-connection-password', 'databases': ['marketing', 'metering']}
        response = client.post('/api/v1/sources', json=payload)
        assert response.status_code == 201, response.text
        source = response.json()
        assert source['host'] == '127.0.0.1'
        assert source['databases'] == ['marketing', 'metering']
        assert source['has_password'] is True
        assert payload['password'] not in response.text
        changed = client.patch(f'/api/v1/sources/{source["id"]}', json={**payload, 'name': '业务只读连接', 'password': None, 'databases': ['marketing']})
        assert changed.status_code == 200, changed.text
        assert changed.json()['name'] == '业务只读连接'
        assert changed.json()['has_password'] is True
        assert changed.json()['databases'] == ['marketing']
        assert payload['password'] not in client.get('/api/v1/sources').text
        assert client.post('/api/v1/sources', json={**payload, 'host': None, 'database': None}).status_code == 422
        import sqlite3
        with sqlite3.connect(tmp_path / 'app.db') as db:
            stored = db.execute('SELECT password_ciphertext FROM source_connections').fetchone()[0]
        assert stored and payload['password'] not in stored


def test_screenshot_upload_is_private_and_does_not_invent_ocr(tmp_path):
    import base64
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
    with client_for(tmp_path) as client:
        response = client.post('/api/v1/modeling/attachments', content=png, headers={'Content-Type': 'image/png'})
        assert response.status_code == 201, response.text
        attachment = response.json()
        assert attachment['ocr_status'] == 'not_configured'
        assert client.get(attachment['url']).content == png
        assert client.post('/api/v1/modeling/attachments', content=b'not-an-image', headers={'Content-Type': 'image/png'}).status_code == 422
        client.cookies.clear()
        assert client.get(attachment['url']).status_code == 401


def test_model_business_context_persists_and_enters_generation_without_becoming_uploaded_material(tmp_path):
    with client_for(tmp_path) as client:
        model=client.post('/api/v1/modeling/models',json={'name':'业务流程建模','group':'测试'}).json()
        other=client.post('/api/v1/modeling/models',json={'name':'另一个模型','group':'测试'}).json()
        context='客户先办理开户，再安装计量装置；一个客户可以拥有多块电表。'
        saved=client.post('/api/v1/modeling/models/'+model['id']+'/context',json={'text':context})
        assert saved.status_code==200,saved.text
        assert client.get('/api/v1/modeling/models/'+model['id']).json()['business_context']==context
        assert client.get('/api/v1/modeling/models/'+other['id']).json()['business_context']==''
        assert client.get('/api/v1/materials').json()['items']==[]
        ref=upload(client,'schema.sql',DDL,'ddl')
        payload={'materials':[ref],'request_key':str(uuid4()),'model_id':model['id']}
        generated=client.post('/api/v1/modeling/runs',json=payload)
        assert generated.status_code==201,generated.text
        run=generated.json()
        assert run['status']=='succeeded',run
        notes=[m for m in run['result']['materials'] if m.get('source_kind')=='model_context']
        assert len(notes)==1 and notes[0]['body']==context
        assert len(client.get('/api/v1/materials').json()['items'])==1
        client.post('/api/v1/modeling/models/'+model['id']+'/context',json={'text':context+' 计量装置记录安装时间。'})
        assert client.post('/api/v1/modeling/runs',json=payload).status_code==409
        assert client.get('/api/v1/modeling/runs/'+run['id']).json()['result']['materials']==run['result']['materials']


def test_failed_generation_retains_previous_draft_and_trace_cannot_reference_unknown_attachment(tmp_path):
    with client_for(tmp_path) as client:
        model=client.post('/api/v1/modeling/models',json={'name':'保留草稿','group':'测试'}).json()
        good=upload(client,'schema.sql',DDL,'ddl')
        first=client.post('/api/v1/modeling/runs',json={'materials':[good],'request_key':str(uuid4()),'model_id':model['id']}).json()
        broken=upload(client,'bad.sql','CREATE TABLE broken (','ddl')
        failed=client.post('/api/v1/modeling/runs',json={'materials':[broken],'request_key':str(uuid4()),'model_id':model['id']}).json()
        assert failed['status']=='failed'
        assert client.get('/api/v1/modeling/models/'+model['id']).json()['run']['id']==first['id']
        assert client.post('/api/v1/modeling/trace',json={'fields':['站点名称'],'attachment_ids':[str(uuid4())]}).status_code==422


def test_workbench_migration_keeps_existing_run_and_snapshot(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    import sqlite3
    path=tmp_path/'migration.db'
    monkeypatch.setenv('DATABASE_URL','sqlite+aiosqlite:///'+str(path))
    config=Config('backend/alembic.ini')
    command.upgrade(config,'0005_identity')
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO modeling_runs (id,workspace_id,request_key,input_sha256,status,revision,input_json) VALUES ('old-run','local-workspace','key','hash','failed',1,'{}')")
        db.execute("INSERT INTO adopted_models (id,workspace_id,run_id,revision,snapshot_json,artifacts_json) VALUES ('old-snapshot','local-workspace','old-run',1,'{}','{}')")
    command.upgrade(config,'head')
    with sqlite3.connect(path) as db:
        row=db.execute('SELECT current_run_id,adopted_id FROM ontology_models').fetchone()
        assert row==('old-run','old-snapshot')
        assert db.execute('SELECT model_id FROM modeling_runs').fetchone()[0]
        assert db.execute('SELECT COUNT(*) FROM trace_attachments').fetchone()[0]==0


@pytest.mark.skipif(os.environ.get('MYSQL_INTEGRATION') != '1', reason='requires local MySQL')
def test_saved_mysql_connection_discovers_selects_and_collects_multiple_databases(tmp_path):
    from sgtrace_app.modules.modeling.engine import build_model
    with client_for(tmp_path) as client:
        payload={'name':'本地结构联调','kind':'mysql','host':os.environ.get('MYSQL_HOST','127.0.0.1'),
                 'port':int(os.environ.get('MYSQL_PORT','3306')),'username':os.environ['MYSQL_USER'],
                 'password':os.environ['MYSQL_PASSWORD'],'databases':['sgtrace_trial_yx186','sgtrace_trial_cjxt']}
        probe=client.post('/api/v1/sources/probe',json=payload)
        assert probe.status_code==200,probe.text
        assert set(payload['databases'])<=set(probe.json()['databases'])
        source=client.post('/api/v1/sources',json=payload).json()
        sid=source['id']
        assert client.post(f'/api/v1/sources/{sid}/test').status_code==200
        assert set(payload['databases'])<=set(client.get(f'/api/v1/sources/{sid}/databases').json()['items'])
        saved=client.post(f'/api/v1/sources/{sid}/materials')
        assert saved.status_code==201,saved.text
        item=saved.json()
        material=client.get(f'/api/v1/materials/{item["id"]}/revisions/{item["revision"]}/content').json()
        assert 'CREATE TABLE' in material['body']
        built=build_model([{'id':item['id'],'name':material['name'],'body':material['body'],'category':'ddl'}])
        assert built['stats']['tables']==14
        assert {table['schema'] for table in built['tables'].values()}==set(payload['databases'])
        # Keeping the password on edit must support reconnect, not only redacted listing.
        response=client.patch(f'/api/v1/sources/{sid}',json={**payload,'password':None,'databases':['sgtrace_trial_yx186']})
        assert response.status_code==200
        assert client.post(f'/api/v1/sources/{sid}/test').status_code==200
        assert client.get(f'/api/v1/sources/{sid}/databases').status_code==200
