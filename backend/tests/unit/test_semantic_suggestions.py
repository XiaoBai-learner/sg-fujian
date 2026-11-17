from sgtrace_app.modules.modeling.engine import build_model
from sgtrace_app.modules.modeling.semantics import enhance
from test_schema_sql_modeling import inputs

def test_llm_cannot_add_a_physical_field_or_accept_unlocatable_evidence():
 result=build_model(inputs()); original=result['draft']['items'][0].copy()
 enhance(result,inputs(),lambda _: {'suggestions':[{'id':original['id'],'name':'猜测名称','description':'猜测','material_id':'ddl-1','quote':'不存在的证据'}]})
 assert result['draft']['items'][0]==original
 assert any(d['code']=='semantic_evidence_invalid' for d in result['diagnostics'])

def test_semantics_accepts_only_known_candidate_and_exact_quote():
 result=build_model(inputs()); c=result['draft']['classes'][0]
 enhance(result,inputs(),lambda _: {'suggestions':[{'id':c['id'],'name':'售电客户','description':'来自表注释','material_id':'ddl-1','quote':"COMMENT='售电客户'"}]})
 assert c['name']=='售电客户'
 assert result['semantic']['accepted']==1
 assert all(i['concept']=='售电客户' for i in result['draft']['items'] if i['conceptId']==c['id'])

def test_valid_quote_for_a_different_candidate_cannot_rename_this_field():
 result=build_model(inputs())
 amount=next(i for i in result['draft']['items'] if i['sources']==['power.INVOICE.DUE'] and i['kind']=='direct')
 enhance(result,inputs(),lambda _: {'suggestions':[{'id':amount['id'],'name':'客户编号','description':'偷换引用','material_id':'ddl-1','quote':"NO VARCHAR(30) COMMENT '客户编号'"}]})
 assert amount['name']=='应收金额'
