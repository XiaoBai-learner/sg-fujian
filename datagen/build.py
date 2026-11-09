"""一键生成 PoC 测试数据集。用法：python3 datagen/build.py

输出到 data/（可随时删除重建，结果确定）：
  inputs/   客户会提供的东西：DDL、样例数据、热点 SQL、DataWorks 血缘导出、需求（截图 OCR 文本）
  gold/     标准答案：本体、R2RML、字段溯源答案（PoC 流水线不能读取）
  sandbox/  SQLite 沙箱库，用于跑 SQL、做值校验、执行 R2RML
"""
import csv
import json
import random
import shutil
import sqlite3
from pathlib import Path

from common import SEED, mysql_type, odps_type, oracle_type, sql_str, sqlite_type, stable_pct
from dataplatform import ETLS, build_ods, odps_task_sql, select_sql
from gen import build as gen_rows
from hotsql import HOT_SQL
from lineage import Lineage, equivalents
from ontology import build_ontology_ttl, build_r2rml_ttl
from pages import PAGES, REQUESTS
from sources import TABLES, resolve_comments

ROOT = Path(__file__).resolve().parent.parent / "data"
SYSTEMS = {"yx186": ("营销业务应用系统", "oracle"), "cjxt": ("用电信息采集系统", "oracle"),
           "kf95598": ("95598客服系统", "mysql")}
SAMPLE_ROWS = 200
LINEAGE_DROP_PCT = 20  # 已导出的任务里再随机丢掉 20% 的字段级血缘


# ---------------------------------------------------------------- DDL
def ddl_oracle(tb):
    cols = ",\n".join(f"  {c['name']} {oracle_type(c['t'])}" for c in tb["cols"])
    pk = tb["key"].replace(",", ", ")
    out = [f"CREATE TABLE {tb['schema'].upper()}.{tb['name']} (\n{cols},\n"
           f"  CONSTRAINT PK_{tb['name'][:24]} PRIMARY KEY ({pk})\n);"]
    if tb["tcmt"] and tb["comment"]:
        out.append(f"COMMENT ON TABLE {tb['schema'].upper()}.{tb['name']} IS {sql_str(tb['comment'])};")
    for c in tb["cols"]:
        if c["comment"]:
            out.append(f"COMMENT ON COLUMN {tb['schema'].upper()}.{tb['name']}.{c['name']} IS {sql_str(c['comment'])};")
    return "\n".join(out)


def ddl_mysql(tb):
    lines = []
    for c in tb["cols"]:
        cm = f" COMMENT {sql_str(c['comment'])}" if c["comment"] else ""
        lines.append(f"  `{c['name']}` {mysql_type(c['t'])}{cm}")
    lines.append(f"  PRIMARY KEY (`{tb['key']}`)")
    tc = f" COMMENT={sql_str(tb['comment'])}" if tb["tcmt"] and tb["comment"] else ""
    return f"CREATE TABLE `{tb['name']}` (\n" + ",\n".join(lines) + f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4{tc};"


def ddl_odps(name, comment, cols):
    lines = []
    for c in cols:
        cm = f" COMMENT {sql_str(c['comment'])}" if c["comment"] else ""
        lines.append(f"  {c['name']} {odps_type(c['t'])}{cm}")
    tc = f"\nCOMMENT {sql_str(comment)}" if comment else ""
    return (f"CREATE TABLE IF NOT EXISTS {name} (\n" + ",\n".join(lines) + f"\n){tc}\n"
            f"PARTITIONED BY (dt STRING COMMENT '业务日期')\nLIFECYCLE 3650;")


# ---------------------------------------------------------------- 工具
def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def create_sqlite_table(conn, qname, cols):
    body = ", ".join(f'"{c["name"]}" {sqlite_type(c["t"])}' for c in cols)
    conn.execute(f"CREATE TABLE {qname} ({body})")


def insert_rows(conn, qname, cols, rows):
    names = [c["name"] for c in cols]
    ph = ", ".join("?" for _ in names)
    conn.executemany(f"INSERT INTO {qname} VALUES ({ph})", [[r.get(n) for n in names] for r in rows])


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".") if v != int(v) else (f"{v:.2f}" if abs(v) < 1e6 else str(int(v)))
    return str(v)


# ---------------------------------------------------------------- 主流程
def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    inp, gold, sbx = ROOT / "inputs", ROOT / "gold", ROOT / "sandbox"
    for p in (inp, gold, sbx):
        p.mkdir(parents=True)

    resolve_comments(TABLES)
    rows = gen_rows()

    # ---------- 源系统：沙箱库 + DDL + 样例 ----------
    conns = {}
    main_db = sqlite3.connect(sbx / "platform.db")
    for sysname in SYSTEMS:
        db = sbx / f"{sysname}.db"
        c = sqlite3.connect(db)
        for tb in [t for t in TABLES if t["schema"] == sysname]:
            create_sqlite_table(c, f'"{tb["name"]}"', tb["cols"])
            insert_rows(c, f'"{tb["name"]}"', tb["cols"], rows[(sysname, tb["name"])])
        c.commit()
        c.close()
        main_db.execute(f"ATTACH DATABASE '{db}' AS {sysname}")
        conns[sysname] = db

    for sysname, (title, dialect) in SYSTEMS.items():
        tbs = [t for t in TABLES if t["schema"] == sysname]
        render = ddl_oracle if dialect == "oracle" else ddl_mysql
        head = f"-- {title}（{sysname}）DDL 导出，方言：{dialect}\n-- 表数量：{len(tbs)}\n\n"
        d = inp / "ddl" / "source" / sysname
        d.mkdir(parents=True)
        (d / "schema.sql").write_text(head + "\n\n".join(render(t) for t in tbs) + "\n", encoding="utf-8")
        for tb in tbs:
            data = rows[(sysname, tb["name"])][:SAMPLE_ROWS]
            write_csv(inp / "samples" / "source" / sysname / f"{tb['name']}.csv",
                      [c["name"] for c in tb["cols"]], [[fmt(r.get(c["name"])) for c in tb["cols"]] for r in data])

    # ---------- 中台：ODS 同步 ----------
    ods = build_ods()
    ods_ddls = []
    for o in ods:
        create_sqlite_table(main_db, o["name"], o["cols"])
        src_cols = ", ".join(f'"{c["src"].split(".")[-1]}"' for c in o["cols"])
        main_db.execute(f"INSERT INTO {o['name']} SELECT {src_cols} FROM {o['src_table']}")
        ods_ddls.append(ddl_odps(o["name"], o["comment"], o["cols"]))

    # ---------- 中台：DWD/DWS/ADS ----------
    etl_ddls, tasks = [], []
    for e in ETLS:
        main_db.execute(f"CREATE TABLE {e['name']} AS {select_sql(e)}")
        etl_ddls.append(ddl_odps(e["name"], e["comment"], e["cols"]))
        tasks.append(e)
    main_db.commit()

    d = inp / "ddl" / "platform"
    d.mkdir(parents=True)
    (d / "schema.sql").write_text(
        f"-- 数据中台（MaxCompute 项目 sgfj_dataplatform）DDL 导出\n-- 表数量：{len(ods) + len(ETLS)}\n\n"
        + "\n\n".join(ods_ddls + etl_ddls) + "\n", encoding="utf-8")
    tdir = inp / "dataworks" / "tasks"
    tdir.mkdir(parents=True)
    for e in tasks:
        (tdir / f"{e['task']}.sql").write_text(
            f"-- DataWorks 节点：{e['task']}（ODPS SQL）\n-- 产出表：{e['name']}\n{odps_task_sql(e)};\n", encoding="utf-8")
    for o in ods:
        cols = [c["name"] for c in o["cols"]]
        data = main_db.execute(f"SELECT * FROM {o['name']} LIMIT {SAMPLE_ROWS}").fetchall()
        write_csv(inp / "samples" / "platform" / f"{o['name']}.csv", cols, [[fmt(v) for v in r] for r in data])
    for e in ETLS:
        cur = main_db.execute(f"SELECT * FROM {e['name']} LIMIT {SAMPLE_ROWS}")
        write_csv(inp / "samples" / "platform" / f"{e['name']}.csv",
                  [x[0] for x in cur.description], [[fmt(v) for v in r] for r in cur.fetchall()])

    # ---------- DataWorks 血缘导出（不完整） ----------
    lin = Lineage()
    exported = []
    for ed in lin.edges:
        if not ed["exported"]:
            continue
        if ed["task_type"] == "ODPS_SQL" and stable_pct("lin:" + ed["src"] + ed["dst"]) < LINEAGE_DROP_PCT:
            continue
        exported.append(ed)

    def split(col):
        parts = col.split(".")
        return (".".join(parts[:-1]), parts[-1])

    write_csv(inp / "dataworks" / "lineage_export.csv",
              ["src_table", "src_column", "dst_table", "dst_column", "task_name", "task_type"],
              [[*split(e["src"]), *split(e["dst"]), e["task"], e["task_type"]] for e in exported])

    # ---------- 热点 SQL ----------
    rnd = random.Random(SEED)
    for qid, cnt, user, sql in HOT_SQL:
        main_db.execute(sql).fetchall()  # 确保可执行
    write_csv(inp / "hot_sql" / "query_log.csv", ["query_id", "exec_count_90d", "submitter", "avg_cost_ms", "sql"],
              [[q, n, u, rnd.randint(80, 9000), s] for q, n, u, s in HOT_SQL])

    # ---------- 需求（截图 OCR 结果） + 答案 ----------
    req_dir = inp / "requests"
    req_dir.mkdir(parents=True)
    answers = []
    index_lines = []
    for rid, pid, dept, asked, low_ctx in REQUESTS:
        pg = PAGES[pid]
        exprs = [f[2] if len(f) > 2 else f[1].split(".")[-1] for f in pg["fields"]]
        sql = f"SELECT {', '.join(exprs)} FROM {pg['frm']}"
        if pg.get("where"):
            sql += f" WHERE {pg['where']}"
        sql += f" ORDER BY {pg['order']} LIMIT 6"
        data = main_db.execute(sql).fetchall()
        assert data, f"{pid} 页面查询为空"
        labels = [f[0] for f in pg["fields"]]
        ocr = [] if low_ctx else [pg["nav"], pg["title"]]
        ocr.append("  ".join(labels))
        ocr += ["  ".join(fmt(v) or "-" for v in r) for r in data]
        ocr.append(f"共 {rnd.randint(30, 900)} 条  < 1 2 3 ... >")
        req = {
            "request_id": rid, "from_dept": dept,
            "email_subject": f"【取数需求】{'' if low_ctx else pg['title']}页面字段来源确认",
            "email_body": f"中台同事你好：附件截图{'是' + pg['system'] + '的' + pg['title'] + '页面' if not low_ctx else '是我们日常用的一个页面'}，"
                          f"麻烦帮忙确认以下字段分别来自哪个系统的哪张表、哪个字段：{'、'.join(asked)}。谢谢！",
            "screenshot_ocr": "\n".join(ocr),
            "asked_fields": asked,
        }
        (req_dir / f"{rid}.json").write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding="utf-8")
        index_lines.append([rid, pid, dept, "低" if low_ctx else "正常", len(asked)])

        fmap = {f[0]: f[1] for f in pg["fields"]}
        for lab in asked:
            page_col = fmap[lab]
            is_source_page = page_col.count(".") == 2
            origins, kind, _ = lin.trace(page_col if is_source_page else page_col)
            origins = sorted(origins)
            eq = sorted({x for o in origins for x in equivalents(o)} - set(origins))
            answers.append([rid, pid, lab, "" if is_source_page else page_col, ";".join(origins), kind, ";".join(eq)])

    write_csv(req_dir / "_index.csv", ["request_id", "page_id", "from_dept", "context_level", "n_fields"], index_lines)
    write_csv(gold / "answers.csv",
              ["request_id", "page_id", "field_label", "platform_column", "source_columns", "derivation", "acceptable_equivalents"],
              answers)

    # ---------- 页面定义（真值，含背后表） ----------
    write_csv(gold / "pages.csv", ["page_id", "title", "system", "backing_table", "field_label", "backing_column"],
              [[pid, p["title"], p["system"], p["frm"].split(" ")[0], f[0], f[1]] for pid, p in PAGES.items() for f in p["fields"]])

    # ---------- 完整血缘（真值） ----------
    write_csv(gold / "lineage_full.csv",
              ["src_table", "src_column", "dst_table", "dst_column", "task_name", "derivation", "expr", "in_export"],
              [[*split(e["src"]), *split(e["dst"]), e["task"], e["kind"], e["expr"],
                "Y" if e in exported else "N"] for e in lin.edges])

    # ---------- 本体 + R2RML ----------
    onto, concept_rows = build_ontology_ttl()
    (gold / "ontology_marketing.ttl").write_text(onto, encoding="utf-8")
    (gold / "mapping_marketing.r2rml.ttl").write_text(build_r2rml_ttl(), encoding="utf-8")
    write_csv(gold / "concept_map.csv", ["source_column", "ontology_property", "business_meaning"], concept_rows)

    # ---------- 表清单（真值：噪声表标记） ----------
    tl = [[f"{t['schema']}.{t['name']}", "source", t["schema"], "Y" if t["noise"] else "N"] for t in TABLES]
    tl += [[o["name"], "ods", "platform", "N"] for o in ods]
    tl += [[e["name"], e["layer"], "platform", "Y" if e["noise"] else "N"] for e in ETLS]
    write_csv(gold / "table_catalog.csv", ["table", "layer", "system", "is_noise"], tl)

    main_db.close()
    print(f"源表 {len(TABLES)} 张，中台表 {len(ods) + len(ETLS)} 张，血缘边 {len(lin.edges)}（导出 {len(exported)}），"
          f"热点 SQL {len(HOT_SQL)} 条，需求 {len(REQUESTS)} 个，待溯源字段 {len(answers)} 个")


if __name__ == "__main__":
    main()
