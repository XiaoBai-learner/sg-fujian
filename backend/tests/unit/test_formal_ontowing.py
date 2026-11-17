from sgtrace_app.modules.modeling.engine import build_model
from sgtrace_app.integrations.ontowing.adapter import compile_model
from test_schema_sql_modeling import inputs


def test_real_ontowing_validation_and_turtle_export():
    result=build_model(inputs())
    compiled=compile_model(result['draft'],result['tables'])
    assert compiled['valid'], compiled
    assert compiled['verification']['materialization']=='not_run'
    assert 'rr:column "NO"' in compiled['artifacts']['mapping.ttl']
    assert '客户编号' in compiled['artifacts']['ontology.ttl']
    # Aggregate expression must not become an invented rr:column.
    assert 'SUM(' not in compiled['artifacts']['mapping.ttl']
