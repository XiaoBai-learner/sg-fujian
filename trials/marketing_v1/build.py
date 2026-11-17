"""Build synthetic trial inputs and a separate, reference-lineage answer key."""
from __future__ import annotations

import csv
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
REFERENCE = ROOT / "reference/poc"
sys.path.insert(0, str(REFERENCE / "datagen"))
try:
    from dataplatform import ETLS
finally:
    sys.path.pop(0)

SCHEMA_MAP = {name: f"sgtrace_trial_{name}" for name in ("yx186", "cjxt", "kf95598")}
PLATFORM = "sgtrace_trial_platform"
INPUT_CATEGORIES = {
    "01_source_ddl.sql": "ddl",
    "02_lineage_views.sql": "sql",
    "03_hot_queries.sql": "sql",
    "04_report_fields.sql": "sql",
}
DIRECT = {
    "dwd_yx_kh_jbxx": "hh hm ydsz gddw_bm gddw_mc hylb ydlb gddy htrl yhzt lhrq xhrq",
    "dwd_yx_jld_xx": "jldbh jldmc dnbzcbh ccbh sccj zhbl zbrq jldzt",
    "dwd_yx_df_ysmx": "ysbs dfny jsdl ysje ssje wyj jqbz fxrq",
    "dwd_yx_jf_mx": "jfbs jfsj jfje jffs sfdw",
    "dwd_yx_cbsz": "cbbs cbny sccbsz bccbsz cbrq",
    "dwd_cj_rdl": "sjrq zxygdl zxwgdl zxygsz",
    "dwd_cj_fhqx": "sjsj yggl wggl",
    "dwd_cj_zd_xx": "zdzcbh zdlx zddz yxzt tyrq",
    "dwd_kf_gd_mx": "gdbh slsj ywlx khmc lxdh slnr cldw clzt bjsj hfpf",
}
CALCULATED = {
    "dwd_yx_df_ysmx": "qfje",
    "dwd_yx_cbsz": "cjdl",
    "dws_yx_kh_qf_hz": "qfys ljqfje ljwyj zzqfny",
    "dws_yx_kh_jf_hz": "zjjfsj ljjfje jfcs",
    "dws_yx_kh_ydl_y": "ydl ysdf",
    "dws_kf_gd_tj_y": "tjyf gdzs tsgds bxgds tsl pjmyd",
    "dws_cj_kh_fh_r": "zdfh pjfh",
    "ads_cj_dkh_fh": "fzl",
}
AMBIGUOUS = {
    "户号": ["yx186.C_CONS.CONS_NO", "yx186.A_RCVBL_FLOW.CONS_NO",
           "yx186.A_PAY_FLOW.CONS_NO", "cjxt.E_DATA_MP.CONS_NO", "kf95598.t_kf_workorder.CUST_NO"],
    "联系电话": ["yx186.C_CONTACT.MOBILE", "kf95598.t_kf_workorder.CONTACT_TEL"],
    "客户ID": ["yx186.C_CONS.CONS_ID", "yx186.C_CONTACT.CONS_ID"],
    "电能表资产编号": ["yx186.D_METER.ASSET_NO", "cjxt.E_DATA_MP.METER_ASSET_NO"],
    "mp_id": ["yx186.C_MP.MP_ID", "yx186.C_METER_MP_RELA.MP_ID", "yx186.R_READ.MP_ID", "cjxt.E_DATA_MP.MP_ID"],
    "id": ["cjxt.E_DATA_MP.ID", "cjxt.E_MP_DAY_READ.ID", "cjxt.E_MP_DAY_ENERGY.ID", "cjxt.E_MP_POWER_CURVE.ID"],
    "data_date": ["cjxt.E_MP_DAY_READ.DATA_DATE", "cjxt.E_MP_DAY_ENERGY.DATA_DATE"],
    "org_no": ["yx186.O_ORG.ORG_NO", "yx186.C_CONS.ORG_NO", "cjxt.R_TMNL_RUN.ORG_NO"],
    "t_factor": ["yx186.D_METER.T_FACTOR", "cjxt.E_DATA_MP.T_FACTOR"],
    "status_code": ["yx186.C_CONS.STATUS_CODE", "yx186.C_MP.STATUS_CODE"],
}
UNKNOWN = [
    "脱硫效率", "线路线损率", "台区线损率", "变压器油温", "碳排放量",
    "光伏装机容量", "上网电价", "变电站海拔", "杆塔经纬度", "断路器分闸次数",
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def remap_source(source):
    schema, rest = source.split(".", 1)
    return f"{SCHEMA_MAP[schema]}.{rest}"


def build_inputs(output):
    """Only source DDL, task SQL, hot logs and column comments; no gold access."""
    folder = output / "inputs"
    folder.mkdir(parents=True, exist_ok=True)
    sources, origins, creates = [], {}, []
    for schema, local in SCHEMA_MAP.items():
        path = REFERENCE / f"data/inputs/ddl/mysql/{schema}.sql"
        origins[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
        for tree in sqlglot.parse(path.read_text(), read="mysql"):
            if not isinstance(tree, exp.Create) or tree.kind != "TABLE":
                continue
            table = tree.this.this.name
            if table.endswith("_HIS") or "_BAK_" in table or table.startswith("TMP_"):
                continue
            tree.this.this.set("db", exp.to_identifier(local, quoted=True))
            columns = [col.name for col in tree.this.expressions if isinstance(col, exp.ColumnDef)]
            source = {"schema": schema, "local_schema": local, "table": table, "columns": columns}
            sources.append(source)
            creates.append(tree.sql("mysql", pretty=True) + ";")
    (folder / "01_source_ddl.sql").write_text(
        "-- 合成营销域试用；只建表，不含 DROP，不执行在原有业务库。\n\n" + "\n\n".join(creates) + "\n")
    views, definitions = [], {}
    for source in sources:
        name = f"ods_{source['schema']}_{source['table'].lower()}"
        projections = ", ".join(f"`{col}` AS `{col.lower()}`" for col in source["columns"])
        query = sqlglot.parse_one(
            f"SELECT {projections} FROM `{source['local_schema']}`.`{source['table']}`", read="mysql")
        definitions[name] = query
        views.append(f"CREATE VIEW `{PLATFORM}`.`{name}` AS\n{query.sql('mysql', pretty=True)};")
    etls = {e["name"]: e for e in ETLS if not e["noise"]}
    for name, etl in etls.items():
        path = REFERENCE / f"data/inputs/dataworks/tasks/sql_{name}.sql"
        origins[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
        query = sqlglot.parse_one(path.read_text(), read="hive").expression
        for table in query.find_all(exp.Table):
            table.set("db", exp.to_identifier(PLATFORM, quoted=True))
        definitions[name] = query
        views.append(f"-- 来源 {path.relative_to(ROOT)}；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。\n"
                     f"CREATE VIEW `{PLATFORM}`.`{name}` AS\n{query.sql('mysql', pretty=True)};")
    (folder / "02_lineage_views.sql").write_text(
        "-- 原 DataWorks 任务转换为只读视图定义；供建模解析及隔离测试库核对。\n\n" + "\n\n".join(views) + "\n")
    path = REFERENCE / "data/inputs/hot_sql/query_log.csv"
    origins[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
    hot = [row for row in csv.DictReader(path.open()) if int(row["query_id"][1:]) <= 22]
    statements = []
    for row in hot:
        query = sqlglot.parse_one(row["sql"], read="mysql")
        for table in query.find_all(exp.Table):
            table.set("db", exp.to_identifier(PLATFORM, quoted=True))
        row["trial_sql"] = query.sql("mysql")
        statements.append(f"-- {row['query_id']}；模拟90天执行 {row['exec_count_90d']} 次；原始账号 {row['submitter']}\n"
                          + query.sql("mysql", pretty=True) + ";")
    (folder / "03_hot_queries.sql").write_text(
        "-- 取自既有合成热点日志 Q001–Q022，SQL 仅补全隔离测试库名。\n\n" + "\n\n".join(statements) + "\n")
    reports = []
    for name, etl in etls.items():
        columns = ", ".join(f"`{c['name']}` AS `{c['comment']}`" for c in etl["cols"])
        reports.append(f"-- {etl['comment']}；显示名来自既有中台列注释，并非真实客户日志。\n"
                       f"SELECT {columns} FROM `{PLATFORM}`.`{name}`;")
    (folder / "04_report_fields.sql").write_text(
        "-- 补充的页面展示查询：根据原 dataplatform.py 列注释生成中文投影，不含标准答案。\n\n"
        + "\n\n".join(reports) + "\n")
    origins["reference/poc/datagen/dataplatform.py"] = sha256((REFERENCE / "datagen/dataplatform.py").read_bytes()).hexdigest()
    return sources, etls, definitions, hot, origins


def build_answers(output, sources, etls, definitions):
    """Gold comes from pre-existing reference lineage, never the model under test."""
    path = REFERENCE / "data/gold/lineage_full.csv"
    edges = defaultdict(list)
    for edge in csv.DictReader(path.open()):
        edges[(edge["dst_table"], edge["dst_column"])].append(edge)
    physical = {f"{s['schema']}.{s['table']}.{c}" for s in sources for c in s["columns"]}

    def paths(table, column, visited=()):
        current = f"{table}.{column}"
        if current in physical:
            return [[remap_source(current)]]
        if current in visited:
            raise ValueError(f"循环标准血缘：{current}")
        upstream = edges[(table, column)]
        if not upstream:
            raise ValueError(f"缺少独立标准血缘：{current}")
        return [[f"{PLATFORM}.{current}", *p]
                for edge in upstream
                for p in paths(edge["src_table"], edge["src_column"], (*visited, current))]

    def expand(query):
        def replace(node):
            if isinstance(node, exp.Table) and node.db == PLATFORM:
                subquery = expand(definitions[node.name].copy())
                return subquery.subquery(node.alias_or_name)
            return node
        return query.transform(replace)

    questions, answers = [], []
    for category, selections in (("direct", DIRECT), ("calculated", CALCULATED)):
        for table, fields in selections.items():
            etl = etls[table]
            for field in fields.split():
                col = next(c for c in etl["cols"] if c["name"] == field)
                qid = f"M{len(questions) + 1:03d}"
                question = f"“{etl['comment']}”中的“{col['comment']}”"
                question += "如何计算，依赖哪些原表字段？" if category == "calculated" else "来自哪张原表的哪个字段？"
                questions.append({"id": qid, "category": category, "question": question,
                                  "field": col["comment"], "context": etl["comment"]})
                chains = paths(table, field)
                expected = sorted({p[-1] for p in chains})
                if not all(source in {remap_source(p) for p in physical} for source in expected):
                    raise ValueError("标准答案引用了输入集合以外的表")
                expanded = expand(definitions[table].copy()).sql("mysql")
                answers.append({
                    "id": qid, "expected_status": "located", "kind": category,
                    "target": f"{table}.{field}", "sources": expected, "expression": col["expr"],
                    "scope": {"where": etl["where"], "group_by": etl["group"], "from": etl["frm"]},
                    "lineage_paths": chains,
                    "verification_sql": f"SELECT `{field}` AS answer FROM `{PLATFORM}`.`{table}`",
                    "independent_source_sql": f"SELECT `{field}` AS answer FROM ({expanded}) AS gold_source",
                    "answer": ("按任务表达式及完整 JOIN/过滤/分组口径计算；来源：" if category == "calculated" else "原表字段：")
                              + "、".join(expected),
                })
    for field, alternatives in AMBIGUOUS.items():
        qid = f"M{len(questions) + 1:03d}"
        questions.append({"id": qid, "category": "ambiguous", "field": field, "context": "",
                          "question": f"只给出“{field}”，不提供系统或页面，能唯一定位原表字段吗？"})
        alternatives = [[remap_source(source)] for source in alternatives]
        assert all(source[0] in {remap_source(p) for p in physical} for source in alternatives)
        answers.append({"id": qid, "expected_status": "ambiguous", "alternatives": alternatives,
                        "answer": "不能唯一定位。应保留以下候选并要求补充系统或页面，不能任意选一个。",
                        "sources": [], "reason": "同名业务字段或技术列在多个原表存在。"})
    for field in UNKNOWN:
        qid = f"M{len(questions) + 1:03d}"
        questions.append({"id": qid, "category": "not_found", "field": field, "context": "仅限本次输入材料",
                          "question": f"仅根据本次材料，“{field}”来自哪张原表？"})
        answers.append({"id": qid, "expected_status": "not_found", "sources": [],
                        "answer": "本次材料没有提供可验证来源；应未找到或请求补充材料，不能编造表字段。"})
    assert len(questions) == len(answers) == 100
    evaluation = output / "evaluation"
    write_json(evaluation / "questions.json", questions)
    write_json(evaluation / "gold/answers.json", answers)
    write_csv(evaluation / "questions.csv", ["id", "category", "question", "field", "context"], questions)
    write_csv(evaluation / "answer_sheet.csv",
              ["id", "question", "field", "actual_status", "actual_sources", "formula_scope_correct", "notes"],
              [{"id": q["id"], "question": q["question"], "field": q["field"]} for q in questions])
    write_csv(evaluation / "gold/answers.csv",
              ["id", "expected_status", "kind", "target", "sources", "alternatives", "expression", "scope", "answer"],
              [{key: json.dumps(a[key], ensure_ascii=False) if isinstance(a.get(key), (dict, list)) else a.get(key, "")
                for key in ["id", "expected_status", "kind", "target", "sources", "alternatives", "expression", "scope", "answer"]}
               for a in answers])
    return path, questions


def build(output=PACKAGE):
    sources, etls, definitions, hot, origins = build_inputs(output)
    gold_path, questions = build_answers(output, sources, etls, definitions)
    manifest = {
        "dataset": "marketing-trial/1", "synthetic": True,
        "schemas": [*SCHEMA_MAP.values(), PLATFORM],
        "tables": sources, "views": list(definitions),
        "hot_queries": [{"id": q["query_id"], "exec_count_90d": int(q["exec_count_90d"])} for q in hot],
        "reference_sha256": origins,
        "gold_reference_sha256": {str(gold_path.relative_to(ROOT)): sha256(gold_path.read_bytes()).hexdigest()},
        "input_sha256": {name: sha256((output / "inputs" / name).read_bytes()).hexdigest() for name in INPUT_CATEGORIES},
        "questions_sha256": sha256((output / "evaluation/questions.json").read_bytes()).hexdigest(),
        "answers_sha256": sha256((output / "evaluation/gold/answers.json").read_bytes()).hexdigest(),
        "question_count": len(questions),
        "counts": {"tables": len(sources), "columns": sum(len(s["columns"]) for s in sources),
                   "views": len(definitions), "hot_queries": len(hot)},
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    build()
