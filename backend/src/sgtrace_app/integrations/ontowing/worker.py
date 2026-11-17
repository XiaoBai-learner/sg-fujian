"""Private subprocess entry, never imported into the HTTP app."""
import json
import sys
from urllib.parse import quote


def compile_artifacts(payload):
    from app.domain.modeling_profiles import validate_editor
    from app.domain.modeling_artifacts.projection import render_member
    draft,tables=payload['draft'],payload['tables']
    model={'format_version':'wing-model-editor/1','concepts':[],'attributes':[],'relations':[],'annotations':[]}
    for c in draft['classes']:
        model['concepts'].append({'id':c['id'],'name':c['name'],'parents':[c['parentId']] if c.get('parentId') else [],
                                  'disjoint_with':[],'top_category':None,'description':c['description']})
        for alias in c.get('aliases',[]): model['annotations'].append({'subject':c['id'],'key':'alias','value':alias})
    usable=[i for i in draft['items'] if not i.get('excluded') and not i.get('uncertain')]
    for a in usable:
        model['attributes'].append({'id':a['id'],'name':a['name'],'concept_id':a['conceptId'],'datatype':a['datatype'],'aliases':a['aliases'],'sensitivity':'internal'})
    for r in draft['relations']:
        if r.get('uncertain'): continue
        model['relations'].append({'id':r['id'],'name':r['name'],'source_id':r['sourceId'],'target_id':r['targetId'],
                                  'symmetric':r['symmetric'],'transitive':r['transitive'],'functional':r['functional'],'inverse_id':None})
    pipeline={'format_version':'wing-pipeline-editor/2','fact_planes':[],'bindings':[]}
    snapshots={'profile':'current-fact-plane-definitions/2','items':[]}
    classes={c['id']:c for c in draft['classes']}
    problems=[]
    bindings={}
    for index,c in enumerate(draft['classes'],1):
        table=tables[c['table']]
        direct=[a for a in usable if a['conceptId']==c['id'] and a['kind']=='direct']
        if not direct: continue
        if not table['keys']:
            problems.append({'code':'missing_entity_key','message':c['name']+' 没有非空主键，无法生成实体映射。'}); continue
        ref={'teiid_id':'local-metadata','data_source_id':str(index),'schema_name':table['schema'],'table_name':table['name'],
             'active_vdb_version':'1','data_source_revision':'1','model_name':'metadata','query_availability':'available','columns_truncated':False}
        binding={'id':'binding_'+c['id'],'concept_id':c['id'],**ref,'key_columns':table['keys'],'attributes':[],'references':[]}
        for a in direct:
            if len(a['sources'])!=1 or a['sources'][0].rsplit('.',1)[0]!=c['table']:
                problems.append({'code':'mapping_owner_changed','message':a['name']+' 的所属类与原始字段映射不一致。'}); continue
            binding['attributes'].append({'attribute_id':a['id'],'column':a['sources'][0].rsplit('.',1)[1]})
        pipeline['fact_planes'].append(ref); pipeline['bindings'].append(binding); bindings[c['id']]=binding
        snapshots['items'].append({'reference':ref,'dictionary':{'table_name':table['name'],'columns':[
            {'name':col['name'],'data_type':col['type'].split('(')[0].lower(),'nullable':col['nullable'],'primary_key':col['name'] in table['keys'],'position':i}
            for i,col in enumerate(table['columns'])]}})
    for r in draft['relations']:
        if r.get('uncertain'): continue
        child,parent=bindings.get(r['sourceId']),bindings.get(r['targetId'])
        if not child or not parent: continue
        joins=r.get('joins',[])
        if {j['parent'] for j in joins}!=set(parent['key_columns']):
            problems.append({'code':'relation_mapping_invalid','message':r['name']+' 的 JOIN 未覆盖当前终点类主键，需维护映射。'}); continue
        child['references'].append({'relation_id':r['id'],'parent_binding_id':parent['id'],'joins':joins})
    reports={kind:validate_editor(json.dumps(editor).encode(),kind,**({'model':json.dumps(model).encode(),'model_id':'b626f2a7-9034-4b60-b087-c99fc42281a7','fact_plane_snapshots':json.dumps(snapshots).encode()} if kind=='pipeline' else {}))
             for kind,editor in [('model',model),('pipeline',pipeline)]}
    valid=not problems and all(report['valid'] for report in reports.values()) and bool(pipeline['bindings'])
    artifacts={}; losses=[]
    if valid:
        for kind,editor in [('model',model),('pipeline',pipeline)]:
            out=render_member(kind,editor,'b626f2a7-9034-4b60-b087-c99fc42281a7',model=model)
            artifacts['ontology.ttl' if kind=='model' else 'mapping.ttl']=out['content'].decode() if isinstance(out['content'],bytes) else out['content']
            losses.extend(out.get('losses',[]))
    return {'valid':valid,'reports':reports,'problems':problems,'artifacts':artifacts,'losses':sorted(set(losses)),
            'pipeline':pipeline,'model':model,'verification':{'static':'pass' if valid else 'issues','materialization':'not_run','business_semantics':'not_verified'}}

if __name__=='__main__':
    sys.path.insert(0,sys.argv[1])
    try: result=compile_artifacts(json.loads(sys.stdin.buffer.read(15_000_001)))
    except Exception as error: result={'error':type(error).__name__}
    sys.stdout.write(json.dumps(result,ensure_ascii=False))
