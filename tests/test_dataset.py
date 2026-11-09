"""测试数据集自洽性校验。运行：python3 -m pytest tests -q（会先重新生成 data/）。"""
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "datagen"))
DATA = ROOT / "data"


@pytest.fixture(scope="session", autouse=True)
def built():
    import build
    build.main()


@pytest.fixture(scope="session")
def db():
    conn = sqlite3.connect(DATA / "sandbox" / "platform.db")
    for s in ("yx186", "cjxt", "kf95598"):
        conn.execute(f"ATTACH DATABASE '{DATA / 'sandbox' / (s + '.db')}' AS {s}")
    yield conn
    conn.close()


def read_csv(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def answers():
    return read_csv(DATA / "gold" / "answers.csv")


def ddl_columns():
    """从 inputs 里的 DDL 解析出 源表.列 集合，确认答案只引用客户能看到的字段。"""
    cols = set()
    for sysdir in (DATA / "inputs" / "ddl" / "source").iterdir():
        text = (sysdir / "schema.sql").read_text(encoding="utf-8")
        for m in re.finditer(r"CREATE TABLE (?:[A-Z0-9_]+\.)?`?(\w+)`? \((.*?)\n\)", text, re.S):
            for line in m.group(2).splitlines():
                tok = line.strip().strip("`").split("`")[0].split(" ")[0]
                if tok and tok != "CONSTRAINT" and tok != "PRIMARY":
                    cols.add(f"{sysdir.name}.{m.group(1)}.{tok}")
    return cols


def test_every_answer_points_to_real_source_column():
    cols = ddl_columns()
    for a in answers():
        for c in a["source_columns"].split(";"):
            assert c in cols, f"{a['request_id']} {a['field_label']} -> {c} 不在源 DDL 中"


def test_every_asked_field_has_answer():
    got = {(a["request_id"], a["field_label"]) for a in answers()}
    for p in (DATA / "inputs" / "requests").glob("R*.json"):
        r = json.loads(p.read_text(encoding="utf-8"))
        for f in r["asked_fields"]:
            assert (r["request_id"], f) in got
            assert f in r["screenshot_ocr"], "询问的字段必须出现在截图上"


def test_direct_answers_hold_on_values(db):
    """直接映射的字段：页面背后列的取值必须是源字段取值的子集（值校验思路的真值保证）。"""
    checked = 0
    for a in answers():
        if a["derivation"] != "direct" or not a["platform_column"]:
            continue
        t, c = a["platform_column"].split(".")
        src = a["source_columns"].split(";")[0]
        s_schema, s_table, s_col = src.split(".")
        missing = db.execute(
            f'SELECT COUNT(*) FROM (SELECT DISTINCT {c} v FROM {t} WHERE {c} IS NOT NULL) '
            f'WHERE v NOT IN (SELECT "{s_col}" FROM {s_schema}."{s_table}" WHERE "{s_col}" IS NOT NULL)'
        ).fetchone()[0]
        assert missing == 0, f"{a['platform_column']} 有 {missing} 个值不在 {src}"
        checked += 1
    assert checked >= 40


def test_ocr_values_exist_in_sandbox(db):
    """截图第一行数据的户号/工单号能在沙箱里查到，保证截图不是凭空编的。"""
    r = json.loads((DATA / "inputs" / "requests" / "R003.json").read_text(encoding="utf-8"))
    first = r["screenshot_ocr"].splitlines()[3].split("  ")
    assert db.execute("SELECT COUNT(*) FROM yx186.A_RCVBL_FLOW WHERE CONS_NO = ?", (first[0],)).fetchone()[0] > 0


def test_lineage_export_is_incomplete_but_full_lineage_covers_answers():
    full = read_csv(DATA / "gold" / "lineage_full.csv")
    exported = read_csv(DATA / "inputs" / "dataworks" / "lineage_export.csv")
    assert 0.6 < len(exported) / len(full) < 0.95
    missing = [e for e in full if e["in_export"] == "N"]
    assert any(e["dst_table"].startswith("ads_") for e in missing), "应当有 ADS 层血缘缺失"


def test_hot_sql_runs(db):
    for q in read_csv(DATA / "inputs" / "hot_sql" / "query_log.csv"):
        db.execute(q["sql"]).fetchall()


def test_noise_tables_not_in_answers():
    noise = {r["table"] for r in read_csv(DATA / "gold" / "table_catalog.csv") if r["is_noise"] == "Y"}
    for a in answers():
        for c in a["source_columns"].split(";"):
            assert ".".join(c.split(".")[:2]) not in noise


def test_comments_are_partially_missing():
    text = (DATA / "inputs" / "ddl" / "source" / "cjxt" / "schema.sql").read_text(encoding="utf-8")
    n_cols = len(re.findall(r"^\s+[A-Z_]+ (?:NUMBER|VARCHAR2|DATE)", text, re.M))
    n_cmt = text.count("COMMENT ON COLUMN")
    assert n_cmt < n_cols * 0.5, "采集系统注释应当大量缺失"


def test_rdf_parses_and_r2rml_covers_answer_columns():
    onto = rdflib.Graph().parse(DATA / "gold" / "ontology_marketing.ttl")
    mapping = rdflib.Graph().parse(DATA / "gold" / "mapping_marketing.r2rml.ttl")
    assert len(onto) > 300 and len(mapping) > 300
    rr = rdflib.Namespace("http://www.w3.org/ns/r2rml#")
    mapped = set()
    for tm in mapping.subjects(rdflib.RDF.type, rr.TriplesMap):
        lt = mapping.value(tm, rr.logicalTable)
        tname = mapping.value(lt, rr.tableName)
        if tname is None:
            continue
        for pom in mapping.objects(tm, rr.predicateObjectMap):
            om = mapping.value(pom, rr.objectMap)
            col = mapping.value(om, rr.column)
            if col is not None:
                mapped.add(f"{tname}.{col}")
    for a in answers():
        for c in a["source_columns"].split(";"):
            assert c in mapped, f"R2RML 没有覆盖 {c}"
