import pytest
from sgtrace_app.modules.modeling.engine import build_model

DDL = """CREATE TABLE power.CLIENT (
 ID BIGINT NOT NULL PRIMARY KEY COMMENT '内部标识',
 NO VARCHAR(30) COMMENT '客户编号', NAME VARCHAR(40) COMMENT '客户名称'
) COMMENT='售电客户';
CREATE TABLE power.INVOICE (
 ID BIGINT NOT NULL PRIMARY KEY, CLIENT_ID BIGINT NOT NULL,
 DUE DECIMAL(12,2) COMMENT '应收金额', PAID DECIMAL(12,2) COMMENT '已收金额',
 FOREIGN KEY (CLIENT_ID) REFERENCES power.CLIENT(ID)
) COMMENT='账单';"""
SQL = """WITH b AS (SELECT CLIENT_ID, DUE, PAID FROM power.INVOICE)
SELECT c.NO AS 户号, SUM(b.DUE - b.PAID) AS 待收金额
FROM power.CLIENT c JOIN b ON c.ID = b.CLIENT_ID
WHERE b.DUE > b.PAID GROUP BY c.NO;"""

def inputs(ddl=DDL, sql=SQL):
 return [dict(id='ddl-1', name='结构.sql', category='ddl', body=ddl),
         dict(id='sql-1', name='热点.sql', category='sql', body=sql)]

def test_ddl_sql_build_uses_actual_schema_comments_and_cte_lineage():
 result = build_model(inputs())
 draft = result['draft']
 assert {cls['name'] for cls in draft['classes']} == {'售电客户', '账单'}
 direct = next(item for item in draft['items'] if item['name'] == '客户编号')
 assert direct['sources'] == ['power.CLIENT.NO']
 assert '户号' in direct['aliases']
 measure = next(item for item in draft['items'] if item['name'] == '待收金额')
 assert measure['kind'] == 'calculated'
 assert measure['sources'] == ['power.INVOICE.DUE', 'power.INVOICE.PAID']
 assert 'GROUP BY' in measure['scope'] and 'WHERE' in measure['scope']
 assert any(rel['joins'] == [{'child':'CLIENT_ID','parent':'ID'}] for rel in draft['relations'])
 assert 'yx186' not in str(result)
 for item in draft['classes'] + draft['items'] + draft['relations']:
  for ev in item['evidence']:
   body = next(m['body'] for m in inputs() if m['id'] == ev['materialId'])
   assert body[ev['start']:ev['end']] == ev['quote']

def test_unresolved_sql_never_invents_columns_and_reports_failure():
 result = build_model(inputs(sql='SELECT c.IMAGINARY AS 隐藏字段 FROM power.CLIENT c;'))
 assert not any('IMAGINARY' in str(item) for item in result['draft']['items'])
 assert any(d['code'] == 'sql_unresolved' for d in result['diagnostics'])

def test_missing_key_or_missing_semantics_is_not_silently_promoted():
 result = build_model(inputs(ddl='CREATE TABLE mystery.T (v TEXT);', sql='SELECT v FROM mystery.T;'))
 assert result['draft']['classes'][0]['uncertain'] is True
 assert any(d['code'] == 'missing_entity_key' for d in result['diagnostics'])

def test_ambiguous_schema_or_same_label_is_not_merged_by_name():
 ddl = "CREATE TABLE a.X (id INT NOT NULL PRIMARY KEY, name TEXT COMMENT '名称') COMMENT='对象'; CREATE TABLE b.X (id INT NOT NULL PRIMARY KEY, name TEXT COMMENT '名称') COMMENT='对象';"
 result = build_model(inputs(ddl=ddl, sql='SELECT name FROM X;'))
 assert len(result['draft']['classes']) == 2
 assert len({c['id'] for c in result['draft']['classes']}) == 2
 assert any(d['code'] == 'sql_unresolved' for d in result['diagnostics'])

def test_wildcard_and_insert_select_are_parsed_without_execution():
 result = build_model(inputs(sql='INSERT INTO report.t SELECT c.* FROM power.CLIENT c;'))
 assert result['stats']['queries_parsed'] == 1
 assert {o['name'] for o in result['queries'][0]['outputs']} == {'ID','NO','NAME'}

def test_invalid_ddl_and_no_schema_fail_honestly():
 with pytest.raises(ValueError): build_model(inputs(ddl='CREATE TABLE BROKEN (id', sql=''))
 with pytest.raises(ValueError): build_model([dict(id='sql',name='q.sql',category='sql',body='SELECT 1;')])

def test_repeat_build_is_deterministic_and_does_not_depend_on_material_order():
 assert build_model(inputs()) == build_model(list(reversed(inputs())))

def test_view_expansion_resolves_to_original_table_columns():
 result=build_model(inputs(sql='CREATE VIEW power.client_names AS SELECT NO, NAME FROM power.CLIENT; SELECT NAME AS 显示名称 FROM power.client_names;'))
 assert result['stats']['queries_parsed']==2
 item=next(i for i in result['draft']['items'] if i['sources']==['power.CLIENT.NAME'] and i['kind']=='direct')
 assert '显示名称' in item['aliases']

def test_named_primary_constraint_and_cross_schema_same_column_remain_distinct():
 ddl="CREATE TABLE a.X (ID INT NOT NULL, NAME TEXT COMMENT '名称', CONSTRAINT pk PRIMARY KEY (ID)) COMMENT='甲对象'; CREATE TABLE b.X (ID INT NOT NULL PRIMARY KEY, NAME TEXT COMMENT '名称') COMMENT='乙对象';"
 result=build_model(inputs(ddl=ddl,sql='SELECT a.NAME AS 甲名称, b.NAME AS 乙名称 FROM a.X a JOIN b.X b ON a.ID=b.ID;'))
 assert result['tables']['a.X']['keys']==['ID']
 assert any(i['sources']==['a.X.NAME'] and '甲名称' in i['aliases'] for i in result['draft']['items'])
 assert any(i['sources']==['b.X.NAME'] and '乙名称' in i['aliases'] for i in result['draft']['items'])

def test_multi_table_join_relations_do_not_gain_invented_cardinality():
 result=build_model(inputs(ddl=DDL.replace('FOREIGN KEY (CLIENT_ID) REFERENCES power.CLIENT(ID)','KEY idx (CLIENT_ID)'),sql='SELECT c.NO FROM power.CLIENT c JOIN power.INVOICE i ON c.ID=i.CLIENT_ID;'))
 assert result['draft']['relations'][0]['uncertain'] is True
 assert result['draft']['relations'][0]['cardinality']=='unknown'

def test_string_expression_is_not_assigned_decimal_type():
 result=build_model(inputs(sql="SELECT CONCAT(NAME, '客户') AS 展示名称 FROM power.CLIENT;"))
 prop=next(i for i in result['draft']['items'] if i['kind']=='calculated')
 assert prop['datatype']=='string'

def test_use_context_and_same_named_views_do_not_cross_databases():
 ddl="CREATE TABLE a.T (id INT NOT NULL PRIMARY KEY, v INT COMMENT '甲值') COMMENT='甲'; CREATE TABLE b.T (id INT NOT NULL PRIMARY KEY, v INT COMMENT '乙值') COMMENT='乙';"
 sql="CREATE VIEW a.V AS SELECT v FROM a.T; CREATE VIEW b.V AS SELECT v FROM b.T; USE a; SELECT v AS 甲金额 FROM V;"
 result=build_model(inputs(ddl,sql))
 item=next(i for i in result['draft']['items'] if '甲金额' in i['aliases'])
 assert item['sources']==['a.T.v']

def test_insert_task_dependencies_chain_to_original_columns():
 ddl="CREATE TABLE x.A (id INT NOT NULL PRIMARY KEY, amount INT) COMMENT='原始'; CREATE TABLE x.B (id INT NOT NULL PRIMARY KEY, amount INT) COMMENT='中台';"
 result=build_model(inputs(ddl,'INSERT INTO x.B(id,amount) SELECT id,amount FROM x.A; SELECT amount AS 页面金额 FROM x.B;'))
 item=next(i for i in result['draft']['items'] if '页面金额' in i['aliases'])
 assert item['sources']==['x.A.amount']

def test_same_named_aggregates_with_different_join_context_are_separate_variants():
 ddl="CREATE TABLE x.A (id INT NOT NULL PRIMARY KEY, amount INT) COMMENT='对象甲'; CREATE TABLE x.C (id INT NOT NULL PRIMARY KEY) COMMENT='对象乙';"
 result=build_model(inputs(ddl,'SELECT SUM(a.amount) AS 总金额 FROM x.A a JOIN x.C c ON a.id=c.id; SELECT SUM(a.amount) AS 总金额 FROM x.A a LEFT JOIN x.C c ON a.id=c.id;'))
 metrics=[i for i in result['draft']['items'] if i['kind']=='calculated']
 assert len(metrics)==2
 assert all('总金额' in [i['name'],*i['aliases']] for i in metrics)
 assert metrics[0]['scope']!=metrics[1]['scope']

def test_duplicate_structures_merge_provenance_instead_of_conflicting():
 mats=inputs(sql='')
 mats.append({**mats[0],'id':'ddl-copy'})
 result=build_model(mats)
 assert len(result['tables'])==2
 prop=next(i for i in result['draft']['items'] if i['sources']==['power.CLIENT.NO'])
 assert {e['materialId'] for e in prop['evidence']}=={'ddl-1','ddl-copy'}

def test_insert_without_target_columns_uses_destination_ddl_order():
 ddl="CREATE TABLE x.A(id INT NOT NULL PRIMARY KEY, amount INT) COMMENT='A'; CREATE TABLE x.B(amount INT, id INT NOT NULL PRIMARY KEY) COMMENT='B';"
 result=build_model(inputs(ddl,'INSERT INTO x.B SELECT id,amount FROM x.A; SELECT amount AS 页面金额 FROM x.B;'))
 prop=next(i for i in result['draft']['items'] if '页面金额' in i['aliases'])
 assert prop['sources']==['x.A.id']

def test_conflicting_task_writers_remain_blocked_through_views():
 ddl=';'.join(f"CREATE TABLE x.{t}(id INT NOT NULL PRIMARY KEY, amount INT) COMMENT='{t}'" for t in ['A','B','D'])+';'
 sql='INSERT INTO x.B SELECT id,amount FROM x.A; INSERT INTO x.B SELECT id,amount FROM x.D; CREATE VIEW x.C AS SELECT amount FROM x.B; SELECT amount AS 页面金额 FROM x.C;'
 result=build_model(inputs(ddl,sql))
 assert not any('页面金额' in i['aliases'] for i in result['draft']['items'])
 assert any(d['code']=='sql_unresolved' for d in result['diagnostics'])

def test_unqualified_insert_target_uses_unique_schema_before_backtracking():
 ddl="CREATE TABLE x.A(id INT NOT NULL PRIMARY KEY, amount INT) COMMENT='原始'; CREATE TABLE x.B(amount INT, id INT NOT NULL PRIMARY KEY) COMMENT='中台';"
 result=build_model(inputs(ddl,'INSERT INTO B SELECT id,amount FROM A; SELECT amount AS 页面金额 FROM B;'))
 item=next(i for i in result['draft']['items'] if '页面金额' in i['aliases'])
 assert item['sources']==['x.A.id']
