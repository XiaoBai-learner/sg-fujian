"""溯源服务测试。需要 OntoWing 后端在 ../ontowing/backend（或 ONTOWING_BACKEND）。

运行：.venv/bin/python -m pytest tests -q
R2RML 实跑较慢（约 30 秒），单独标记为 slow：-m "not slow" 可跳过。
"""
import pytest

from sgtrace import metadata, pipeline, wing
from sgtrace.evidence import Evidence

pytestmark = pytest.mark.skipif(not wing.info()["available"], reason="OntoWing 后端不可用")


@pytest.fixture(scope="module")
def result():
    return pipeline.run("ddl", execute_r2rml=False, run_eval=True, write=False)


def test_metadata_ddl_parsing_matches_generated_ddl():
    meta = metadata.from_ddl_files()
    assert len(meta["yx186"]) == 12 and len(meta["cjxt"]) == 5 and len(meta["kf95598"]) == 2
    assert len(meta["sgfj_dataplatform"]) == 41
    cons = meta["yx186"]["C_CONS"]
    assert cons.primary_key == ["CONS_ID"] and ["CONS_NO"] in cons.unique_keys
    assert cons.col("CONS_NO").comment == "用户编号"


def test_task_sql_parsing_recovers_missing_lineage():
    ev = Evidence(metadata.from_ddl_files())
    only_parsed = [e for e in ev.edges.values() if "dataworks_export" not in e.provenance]
    assert ev.stats["edges_only_from_parsing"] == len(only_parsed) > 0
    # ads_yx_kh360 的血缘整体没有导出，只能靠解析任务 SQL 追回
    origins, kind, _ = ev.trace("ads_yx_kh360.ljqf")
    assert origins == {"yx186.A_RCVBL_FLOW.RCVBL_AMT", "yx186.A_RCVBL_FLOW.RCVED_AMT"}
    assert kind == "aggregated"


def test_wing_validates_model_and_pipeline(result):
    v = result.report["wing_validation"]
    assert v["model"]["valid"], v["model"]["diagnostics"]
    assert v["pipeline"]["valid"], v["pipeline"]["diagnostics"]
    assert v["pipeline"]["checks"]["sources"] == "pass"


def test_noise_tables_excluded(result):
    excluded = set(result.build.summary()["tables_excluded"])
    assert excluded == {"yx186.C_CONS_BAK_20230601", "yx186.TMP_CONS_CHK"}


def test_history_table_merged_into_same_concept(result):
    tables = result.build.concepts["Receivable"]["tables"]
    assert set(tables) == {"yx186.A_RCVBL_FLOW", "yx186.A_RCVBL_FLOW_HIS"}


def test_cross_system_relations_inferred(result):
    rels = {(r["child"], r["child_col"]): (r["parent"], r["parent_col"]) for r in result.build.relations}
    assert rels[("kf95598.t_kf_workorder", "CUST_NO")] == ("yx186.C_CONS", "CONS_NO")
    assert rels[("cjxt.E_DATA_MP", "METER_ASSET_NO")] == ("yx186.D_METER", "ASSET_NO")
    # 终端资产号不是电能表资产号，后缀匹配不能误连
    assert ("cjxt.R_TMNL_RUN", "TMNL_ASSET_NO") not in rels


def test_semantic_index_comes_from_exported_files(result):
    sem = result.semantic
    assert "户号" in sem.preds["Consumer_consNo"].alt_labels
    assert ("yx186.C_CONS", "CONS_NO") in sem.preds["Consumer_consNo"].columns
    assert sem.relation_target["WorkOrder_custNo"] == ("yx186.C_CONS", "CONS_NO")


def test_quality_beats_baseline_on_dev_and_holdout(result):
    ev = result.report["evaluation"]
    assert ev["system"]["overall"]["strict"] >= 0.9
    assert ev["holdout"]["overall"]["strict"] >= 0.85
    assert ev["holdout"]["overall"]["strict"] > ev["holdout"]["baseline_keyword"]["strict"] + 0.4


def test_free_question():
    from sgtrace.qa import QAEngine
    r = pipeline.run("ddl", execute_r2rml=False, run_eval=False, write=False)
    q = QAEngine(r.build, r.semantic, r.evidence)
    a = q.answer_question("户号属于什么表？")
    assert a["status"] == "ok" and a["answers"][0]["column"] == "yx186.C_CONS.CONS_NO"
    assert "kf95598.t_kf_workorder.CUST_NO" in {x["column"] for x in a["referenced_by"]}
    d = q.answer_question("欠费金额来自哪个字段")
    assert d["status"] == "derived_only"
    assert set(d["derived_metrics"][0]["sources"]) == {"yx186.A_RCVBL_FLOW.RCVBL_AMT", "yx186.A_RCVBL_FLOW.RCVED_AMT"}
    assert q.answer_question("变压器容量")["status"] == "not_found"


@pytest.mark.slow
def test_r2rml_executes_on_sandbox():
    r = pipeline.run("ddl", execute_r2rml=True, run_eval=False, write=False)
    x = r.report["r2rml_execution"]
    assert x["ran"] and x["passed"], x
    assert x["empty_concepts"] == []
