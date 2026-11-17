"""Evidence-first DDL/SQL modeling. Parsing only: never execute supplied SQL."""
from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
import json
import re

import sqlglot
from sqlglot import exp
from sqlglot.lineage import lineage
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.annotate_types import annotate_types
from sqlglot.optimizer.scope import Scope, traverse_scope
from sqlglot.tokens import TokenType


def identity(kind, *parts):
    return kind + '_' + sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def datatype(sql_type):
    value = sql_type.lower().split('(')[0]
    if value in {'boolean','bool'}: return 'boolean'
    if value in {'date'}: return 'date'
    if value in {'timestamp','datetime'}: return 'datetime'
    if 'int' in value: return 'integer'
    if value in {'decimal','numeric','float','double','real'}: return 'decimal'
    return 'string'


def statements(material):
    body = material['body']
    try:
        boundaries = [t.end + 1 for t in sqlglot.tokenize(body, read='mysql') if t.token_type == TokenType.SEMICOLON]
    except sqlglot.errors.SqlglotError as error:
        raise ValueError('SQL 词法解析失败') from error
    start = 0
    for end in [*boundaries, len(body)]:
        raw = body[start:end]
        if raw.strip():
            try: tree = sqlglot.parse_one(raw, read='mysql')
            except sqlglot.errors.SqlglotError as error: raise ValueError(f'{material["name"]} 第 {body[:start].count(chr(10))+1} 行 SQL 解析失败') from error
            if tree is not None: yield tree, start, end
        start = end


def evidence(material, label, start, end):
    body = material['body']
    return {'materialId':material['id'], 'label':label, 'start':start, 'end':end,
            'line':body[:start].count('\n')+1, 'quote':body[start:end],
            'sourceSha256':sha256(body.encode()).hexdigest()}


def comment_of(node):
    if isinstance(node, exp.ColumnDef):
        return next((c.kind.this.name for c in node.constraints if isinstance(c.kind, exp.CommentColumnConstraint)), '')
    props = node.args.get('properties')
    return next((p.this.name for p in props.expressions if isinstance(p, exp.SchemaCommentProperty)), '') if props else ''


def label_of(comment, fallback):
    return re.split(r'[，,；;\n]', comment.strip())[0][:120] if comment.strip() else fallback


def build_model(materials):
    if not materials or len(materials) > 30 or sum(len(m['body'].encode()) for m in materials) > 5_000_000:
        raise ValueError('建模输入需为 1–30 份材料，总正文不超过 5 MB')
    materials = sorted(materials, key=lambda m:m['id'])
    tables, queries_raw, diagnostics, documents, views = {}, [], [], [], {}
    definitions=[]
    def diagnostic(code, material_id, message):
        diagnostics.append({'code':code,'materialId':material_id,'message':message})
    statement_count = 0
    for material in materials:
        if material['category'] == 'document':
            documents.append(material)
            diagnostic('document_context',material['id'],'业务文档作为语义增强和人工核对材料；结构路径不猜测文档中的新表字段。')
            continue
        current_schema = ''
        for tree, start, end in statements(material):
            statement_count += 1
            if statement_count > 1000: raise ValueError('本轮最多解析 1000 条语句，请拆分材料')
            ev = evidence(material,'DDL 结构',start,end)
            if isinstance(tree, exp.Use):
                current_schema = tree.this.name
            elif isinstance(tree,exp.Create) and tree.kind == 'TABLE' and isinstance(tree.this,exp.Schema) and not tree.expression:
                tab = tree.this.this
                schema = tab.db or current_schema
                if not schema: raise ValueError(f'{material["name"]} 的 {tab.name} 缺少库名；请补充 USE 或 schema.TABLE')
                key = f'{schema}.{tab.name}'
                cols, pk, fks = [], [], []
                for node in tree.this.expressions:
                    if isinstance(node,exp.ColumnDef):
                        if any(isinstance(c.kind,exp.PrimaryKeyColumnConstraint) for c in node.constraints): pk.append(node.name)
                        sql_type = node.args['kind'].sql('mysql')
                        cols.append({'name':node.name,'type':sql_type,'comment':comment_of(node),
                                     'nullable':not any(isinstance(c.kind,exp.NotNullColumnConstraint) for c in node.constraints),
                                     'evidence':[evidence(material,'字段定义',start+node.this.meta['start'],start+max(n.meta.get('end',node.this.meta['end']) for n in node.walk())+1)]})
                    elif isinstance(node,exp.PrimaryKey): pk.extend(x.name for x in node.expressions)
                for constraint in tree.this.find_all(exp.PrimaryKey):
                    pk.extend(x.name for x in constraint.expressions if x.name not in pk)
                for fk in tree.find_all(exp.ForeignKey):
                    ref = fk.args.get('reference')
                    if not ref or not isinstance(ref.this,exp.Schema): continue
                    parent = ref.this.this
                    fks.append({'table':f'{parent.db or schema}.{parent.name}', 'child':[x.name for x in fk.expressions],
                                'parent':[x.name for x in ref.this.expressions]})
                if not cols: raise ValueError(f'{key} 没有可解析字段')
                if len({c['name'] for c in cols}) != len(cols) or any(k not in {c['name'] for c in cols} for k in pk):
                    raise ValueError(f'{key} 字段或主键结构不合法')
                for col in cols:
                    if col['name'] in pk: col['nullable'] = False
                item = {'schema':schema,'name':tab.name,'comment':comment_of(tree),'columns':cols,'keys':pk,'foreign_keys':fks,'evidence':[ev]}
                if key in tables:
                    def structure(value):
                        return {**{k:v for k,v in value.items() if k not in {'evidence','columns'}},
                                'columns':[{k:v for k,v in col.items() if k!='evidence'} for col in value['columns']]}
                    if structure(tables[key]) != structure(item):
                        raise ValueError(f'{key} 存在冲突的 DDL 定义，请选择同一版本')
                    tables[key]['evidence'].append(ev)
                    for existing,col in zip(tables[key]['columns'],cols): existing['evidence'].extend(col['evidence'])
                else: tables[key] = item
            elif isinstance(tree,exp.Query): queries_raw.append((tree,material,start,end,current_schema))
            elif isinstance(tree,exp.Insert) and isinstance(tree.expression,exp.Query):
                target=tree.this.this if isinstance(tree.this,exp.Schema) else tree.this
                target_db=target.db or current_schema
                destination=f'{target_db}.{target.name}' if target_db else target.name
                columns=[x.name for x in tree.this.expressions] if isinstance(tree.this,exp.Schema) else []
                definitions.append((destination,tree.expression.copy(),target_db,columns,material))
                queries_raw.append((tree.expression,material,start,end,current_schema))
            elif isinstance(tree,exp.Create) and isinstance(tree.expression,exp.Query):
                table = tree.this.this if isinstance(tree.this,exp.Schema) else tree.this
                view_db=table.db or current_schema
                definitions.append((f'{view_db}.{table.name}' if view_db else table.name,tree.expression.copy(),view_db,[],material))
                queries_raw.append((tree.expression,material,start,end,view_db))
            else: diagnostic('unsupported_statement',material['id'],f'未执行、未推断此类语句：{type(tree).__name__}')
    if not tables: raise ValueError('没有可用的 CREATE TABLE 结构；请先提供带库名的 MySQL DDL')
    if len(tables) > 100 or sum(len(t['columns']) for t in tables.values()) > 2000: raise ValueError('本轮最多 100 张表、2000 个字段，请按领域拆分')
    tables = dict(sorted(tables.items()))
    schema_dict = defaultdict(dict)
    for table in tables.values(): schema_dict[table['schema']][table['name']] = {c['name']:c['type'] for c in table['columns']}
    schemas = list(schema_dict)
    normalized_definitions=[]
    for destination,definition,db,columns,material in definitions:
        if '.' not in destination:
            matches=[key for key in tables if key.rsplit('.',1)[-1]==destination]
            if len(matches)==1: destination=matches[0]
            elif len(schemas)==1: destination=f'{schemas[0]}.{destination}'
            else: raise ValueError('视图或任务目标库名不明确，请使用 schema.TABLE 或 USE')
        normalized_definitions.append((destination,definition,db or destination.rsplit('.',1)[0],columns,material))
    definitions=normalized_definitions
    canonical_table = {key.casefold():key for key in tables}
    relation_names=set(tables)|{d[0] for d in definitions}
    blocked=set()
    def bind_sources(query,default_db):
        query=query.copy()
        for scope in traverse_scope(query):
            for source in scope.sources.values():
                if not isinstance(source,exp.Table) or source.db: continue
                if default_db: source.set('db',exp.to_identifier(default_db)); continue
                matches={k for k in relation_names if k.rsplit('.',1)[-1].casefold()==source.name.casefold()}
                if len(matches)>1: raise ValueError('ambiguous schema')
                if len(matches)==1:
                    key=next(iter(matches))
                    if '.' in key: source.set('db',exp.to_identifier(key.rsplit('.',1)[0]))
        return query
    for destination,definition,db,columns,material in definitions:
        try:
            definition=bind_sources(definition,db or (schemas[0] if len(schemas)==1 else ''))
            if not columns and destination in tables: columns=[c['name'] for c in tables[destination]['columns']]
            if columns:
                definition=qualify(definition,dialect='mysql',schema=dict(schema_dict),validate_qualify_columns=True,identify=False)
                if len(columns)!=len(definition.selects): raise ValueError('insert arity mismatch')
                definition.set('expressions',[exp.alias_(projection.this.copy() if isinstance(projection,exp.Alias) else projection.copy(),name,quoted=True) for name,projection in zip(columns,definition.selects)])
            if destination in views and views[destination].sql()!=definition.sql(): blocked.add(destination)
            else: views[destination]=definition
        except (ValueError,sqlglot.errors.SqlglotError):
            blocked.add(destination)
            diagnostic('task_definition_unresolved',material['id'],f'{destination} 的视图或任务定义未完整解析。')
    # Conflicting writers and recursive definitions cannot choose an arbitrary upstream.
    dependencies={name:{f'{t.db}.{t.name}' if t.db else t.name for t in query.find_all(exp.Table)} & set(views) for name,query in views.items()}
    def cyclic(node,path):
        return node in path or any(cyclic(dep,path|{node}) for dep in dependencies.get(node,set()))
    blocked.update(name for name in views if cyclic(name,set()))
    while True:
        dependent={name for name,deps in dependencies.items() if deps & blocked}
        if dependent <= blocked: break
        blocked.update(dependent)

    def resolve(table, column):
        key = f'{table.db}.{table.name}' if table.db else next((k for k in tables if k.rsplit('.',1)[1].casefold() == table.name.casefold()), '')
        if not table.db and sum(k.rsplit('.',1)[1].casefold() == table.name.casefold() for k in tables) != 1: return None
        key = canonical_table.get(key.casefold())
        if not key: return None
        col = next((c['name'] for c in tables[key]['columns'] if c['name'].casefold() == column.casefold()),None)
        return f'{key}.{col}' if col else None
    def leaves(node):
        result = []
        for leaf in node.walk():
            if not leaf.downstream and isinstance(leaf.expression,exp.Table):
                col = exp.to_column(leaf.name).name
                physical = resolve(leaf.expression,col)
                if physical: result.append(physical)
                else: raise ValueError('unresolved source')
            elif not leaf.downstream and isinstance(leaf.expression,exp.Placeholder): raise ValueError('unresolved column')
        return sorted(set(result))
    query_results, sql_relations, aliases = [], [], defaultdict(set)
    for query, material,start,end,default_db in queries_raw:
        try:
            # Expand known view definitions; CTEs/subqueries are resolved by sqlglot scopes.
            bound=bind_sources(query,default_db or (schemas[0] if len(schemas)==1 else ''))
            if any((f'{t.db}.{t.name}' if t.db else t.name) in blocked for t in bound.find_all(exp.Table)): raise ValueError('conflicting task definitions')
            expanded = exp.expand(bound, {k:v for k,v in views.items() if k not in blocked}, dialect='mysql') if views else bound
            qualified = qualify(expanded,dialect='mysql',schema=dict(schema_dict),db=schemas[0] if len(schemas)==1 else None,
                                identify=False,validate_qualify_columns=True)
            typed = annotate_types(qualified.copy(),schema=dict(schema_dict),dialect='mysql')
            output_types = {s.alias_or_name: datatype(s.type.sql('mysql')) if s.type else 'string' for s in typed.selects}
            nodes = lineage(None,qualified,schema=dict(schema_dict),dialect='mysql')
            outputs=[]
            for name,node in nodes.items():
                sources=leaves(node)
                if not sources:
                    diagnostic('constant_output',material['id'],f'{name} 是常量或无物理依赖的输出，不生成字段来源。')
                    continue
                expression = node.expression.this if isinstance(node.expression,exp.Alias) else node.expression
                # A passthrough CTE remains direct only if all intermediate expressions are columns.
                calculated = any(isinstance(n.expression,exp.Alias) and not isinstance(n.expression.this,exp.Column) for n in node.walk())
                kind = 'calculated' if calculated or len(sources)!=1 else 'direct'
                outputs.append({'name':name,'sources':sources,'kind':kind,'datatype':output_types.get(name,'string'),'expression':expression.sql('mysql')})
                if kind=='direct': aliases[sources[0]].add(name)
            ev=evidence(material,'SQL 投影、过滤与粒度',start,end)
            result={'id':identity('query',material['id'],start,end),'outputs':outputs,'sql':query.sql('mysql'),
                    'scope':qualified.sql('mysql'), 'evidence':ev}
            query_results.append(result)
            for scope in traverse_scope(qualified):
                for join in scope.expression.args.get('joins',[]):
                    on=join.args.get('on')
                    if on is None or on.find(exp.Or): continue
                    pairs=[]
                    for eq in on.find_all(exp.EQ):
                        if not isinstance(eq.left,exp.Column) or not isinstance(eq.right,exp.Column): continue
                        def physical(col):
                            src=scope.sources.get(col.table)
                            if isinstance(src,exp.Table): return resolve(src,col.name)
                            if isinstance(src,Scope):
                                ns=lineage(col.name,src.expression,schema=dict(schema_dict),dialect='mysql')
                                ls=leaves(ns)
                                return ls[0] if len(ls)==1 else None
                        left,right=physical(eq.left),physical(eq.right)
                        if left and right and left.rsplit('.',1)[0]!=right.rsplit('.',1)[0]: pairs.append((left,right))
                    if pairs: sql_relations.append((pairs,ev))
        except (sqlglot.errors.SqlglotError,ValueError,KeyError,TypeError):
            diagnostic('sql_unresolved',material['id'],f'第 {material["body"][:start].count(chr(10))+1} 行查询无法完整解析到已有结构，未使用其候选。')
    classes,items,relations=[],[],[]
    for key,table in tables.items():
        cid=identity('class',key)
        name=label_of(table['comment'],key)
        if sum(label_of(t['comment'],k)==name for k,t in tables.items())>1: name=f'{name}（{key}）'
        classes.append({'id':cid,'name':name,'aliases':[], 'description':table['comment'] or '技术结构候选，缺少业务定义。',
                        'parentId':None,'evidence':table['evidence'],'uncertain':not bool(table['comment']),'table':key})
        if not table['keys']: diagnostic('missing_entity_key',table['evidence'][0]['materialId'],f'{key} 缺少非空主键；本轮只做候选，不可导出该表的实体映射。')
        for col in table['columns']:
            source=f'{key}.{col["name"]}'
            display=label_of(col['comment'],col['name'])
            if sum(label_of(c['comment'],c['name'])==display for c in table['columns'])>1: display=f'{display}（{col["name"]}）'
            evs=[*col['evidence']]
            for q in query_results:
                if any(source in o['sources'] for o in q['outputs']): evs.append(q['evidence'])
            unit = re.search(r'(?:单位[：:为\s]*|[，,]\s*)(元|万元|千瓦时|kWh|MW|MWh|kW|%)',col['comment'])
            items.append({'id':identity('property',source),'name':display,'aliases':sorted(aliases[source]-{display}),
                          'concept':name,'conceptId':cid,'description':col['comment'] or '缺少字段业务注释；仅使用结构名和查询别名。',
                          'datatype':datatype(col['type']),'unit':unit.group(1) if unit else '', 'kind':'direct','sources':[source],'evidence':evs})
        for fk in table['foreign_keys']:
            parent=tables.get(fk['table'])
            if not parent or len(fk['child'])!=len(fk['parent']) or any(c not in {x['name'] for x in table['columns']} for c in fk['child']) or any(c not in {x['name'] for x in parent['columns']} for c in fk['parent']):
                diagnostic('foreign_key_unresolved',table['evidence'][0]['materialId'],f'{key} 的外键未能完整解析。'); continue
            relations.append({'id':identity('relation',key,fk),'name':f'关联 {label_of(parent["comment"],parent["name"])}',
                              'description':'DDL 外键结构关联，业务动词尚待确认。','sourceId':cid,'targetId':identity('class',fk['table']),
                              'cardinality':'many-to-one' if set(fk['parent'])==set(parent['keys']) else 'unknown',
                              'symmetric':False,'transitive':False,'functional':False,'evidence':table['evidence'],
                              'joins':[{'child':a,'parent':b} for a,b in zip(fk['child'],fk['parent'])],'origin':'foreign_key'})
    for pairs,ev in sql_relations:
        by_tables=defaultdict(list)
        for a,b in pairs:
            ta,ca=a.rsplit('.',1); tb,cb=b.rsplit('.',1)
            if ta>tb: ta,tb,ca,cb=tb,ta,cb,ca
            by_tables[(ta,tb)].append({'child':ca,'parent':cb})
        for (a,b),joins in by_tables.items():
            existing=next((r for r in relations if {r['sourceId'],r['targetId']}=={identity('class',a),identity('class',b)} and
                           {(j['child'],j['parent']) for j in r['joins']} == ({(j['child'],j['parent']) for j in joins} if r['sourceId']==identity('class',a) else {(j['parent'],j['child']) for j in joins})),None)
            if existing: existing['evidence'].append(ev); continue
            rid=identity('join',a,b,sorted(joins,key=lambda j:j['child']))
            if any(r['id']==rid for r in relations): continue
            relations.append({'id':rid,'name':f'查询关联 {tables[b]["name"]}','description':'SQL 等值 JOIN 使用证据，不能据此确定业务关系与基数。',
                              'sourceId':identity('class',a),'targetId':identity('class',b),'cardinality':'unknown','symmetric':False,'transitive':False,'functional':False,
                              'evidence':[ev],'joins':joins,'origin':'sql_join','uncertain':True})
    for q in query_results:
        for output in q['outputs']:
            if output['kind']!='calculated': continue
            source_tables={s.rsplit('.',1)[0] for s in output['sources']}
            owner=next(iter(source_tables)) if len(source_tables)==1 else None
            cid=identity('class',owner) if owner else None
            ident=identity('measure',output['name'],output['sources'],output['expression'],q['scope'])
            existing=next((i for i in items if i['id']==ident),None)
            if existing:
                existing['evidence'].append(q['evidence']); continue
            name=output['name']
            if any(i['name']==name and i['conceptId']==cid for i in items): name=f'{name}（{q["id"][-6:]}）'
            items.append({'id':ident,'name':name,'aliases':[output['name']] if name!=output['name'] else [],'conceptId':cid,'concept':next((c['name'] for c in classes if c['id']==cid),'跨对象计算'),
                          'description':'SQL 派生指标；表达式及筛选范围来自查询，尚未执行业务口径对账。','kind':'calculated','datatype':output['datatype'],'unit':'',
                          'sources':output['sources'],'expression':output['expression'],'scope':q['scope'],'evidence':[q['evidence']], 'uncertain':owner is None})
    return {'draft':{'revision':1,'classes':classes,'items':sorted(items,key=lambda i:i['id']),'relations':sorted(relations,key=lambda r:r['id'])},
            'tables':tables,'queries':query_results,'diagnostics':diagnostics,
            'stats':{'tables':len(tables),'columns':sum(len(t['columns']) for t in tables.values()),'queries_parsed':len(query_results),'statements':statement_count},
            'method':'schema-sql-evidence/1','documents':[{'id':m['id'],'name':m['name'],'body':m['body']} for m in documents]}
