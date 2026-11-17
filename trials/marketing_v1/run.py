"""Local-only trial setup, SQL proof checks and snapshot-pinned field evaluation."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys

import httpx
import sqlglot
from dotenv import load_dotenv
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
SCHEMAS = (
    "sgtrace_trial_yx186", "sgtrace_trial_cjxt", "sgtrace_trial_kf95598", "sgtrace_trial_platform",
)
OUTPUT = ROOT / "artifacts/marketing-trial"


def read_json(path):
    return json.loads(path.read_text())


def check_package():
    manifest = read_json(PACKAGE / "manifest.json")
    hashes = {**{f"inputs/{name}": value for name, value in manifest["input_sha256"].items()},
              "evaluation/questions.json": manifest["questions_sha256"],
              "evaluation/gold/answers.json": manifest["answers_sha256"]}
    for relative, expected in hashes.items():
        if sha256((PACKAGE / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"试用包文件已变化：{relative}；请先确认或重新构建版本")
    return manifest


def can_install(existing_schemas):
    return not set(existing_schemas).intersection(SCHEMAS)


def mysql_engine():
    import os
    load_dotenv(ROOT / ".env")
    if os.environ.get("MYSQL_HOST", "127.0.0.1") not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("试用脚本仅允许本机 MySQL")
    if not os.environ.get("MYSQL_USER"):
        raise ValueError("请在忽略的 .env 中配置 MYSQL_*")
    return create_async_engine(URL.create(
        "mysql+asyncmy", username=os.environ["MYSQL_USER"], password=os.environ.get("MYSQL_PASSWORD", ""),
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"), port=int(os.environ.get("MYSQL_PORT", "3306")),
        query={"charset": "utf8mb4"},
    ), pool_pre_ping=True)


async def install_mysql():
    manifest = check_package()
    sys.path.insert(0, str(ROOT / "reference/poc/datagen"))
    try:
        from gen import build as generate_rows
    finally:
        sys.path.pop(0)
    rows = generate_rows()
    engine = mysql_engine()
    counts = {}
    try:
        async with engine.begin() as connection:
            existing = set((await connection.execute(text("SHOW DATABASES"))).scalars())
            if not can_install(existing):
                raise ValueError("试用库已存在，已停止；请使用 verify-mysql。脚本不会删除或覆盖任何库。")
            for schema in SCHEMAS:
                await connection.exec_driver_sql(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            for filename in ("01_source_ddl.sql", "02_lineage_views.sql"):
                for statement in sqlglot.parse((PACKAGE / "inputs" / filename).read_text(), read="mysql"):
                    if statement is not None:
                        await connection.exec_driver_sql(statement.sql("mysql"))
            for table in manifest["tables"]:
                cols = table["columns"]
                records = rows[(table["schema"], table["table"])]
                query = (f"INSERT INTO `{table['local_schema']}`.`{table['table']}` "
                         f"({', '.join(f'`{c}`' for c in cols)}) VALUES ({', '.join(['%s'] * len(cols))})")
                for offset in range(0, len(records), 1000):
                    batch = [tuple(r.get(col) for col in cols) for r in records[offset:offset + 1000]]
                    await connection.exec_driver_sql(query, batch)
                counts[f"{table['local_schema']}.{table['table']}"] = len(records)
        report = {"dataset": manifest["dataset"], "rows": counts, "row_count": sum(counts.values()),
                  "reference_generator_sha256": sha256((ROOT / "reference/poc/datagen/gen.py").read_bytes()).hexdigest()}
        save_report("mysql-install.json", report)
        return report
    finally:
        await engine.dispose()


def normalized_rows(rows):
    def normalize(value):
        if isinstance(value, (int, float, Decimal)):
            return str(Decimal(str(value)).normalize())
        return None if value is None else str(value)
    return Counter(tuple(normalize(value) for value in row) for row in rows)


async def verify_mysql():
    manifest = check_package()
    gold = read_json(PACKAGE / "evaluation/gold/answers.json")
    engine = mysql_engine()
    results = []
    try:
        async with engine.connect() as connection:
            for answer in gold:
                if answer["expected_status"] != "located":
                    continue
                actual = (await connection.execute(text(answer["verification_sql"]))).all()
                expected = (await connection.execute(text(answer["independent_source_sql"]))).all()
                results.append({"id": answer["id"], "rows": len(actual), "nonempty": bool(actual),
                                "same": normalized_rows(actual) == normalized_rows(expected)})
            hot = sqlglot.parse((PACKAGE / "inputs/03_hot_queries.sql").read_text(), read="mysql")
            for query in hot:
                if query is not None:
                    await connection.execute(text(query.sql("mysql")))
        report = {"dataset": manifest["dataset"], "checked_answers": len(results),
                  "sql_equal": sum(r["same"] for r in results), "nonempty": sum(r["nonempty"] for r in results),
                  "hot_queries_executed": len(manifest["hot_queries"]), "results": results,
                  "scope": "视图转换与独立原表查询结果一致性；不证明客户业务口径或建模准确率。"}
        save_report("mysql-verification.json", report)
        if report["sql_equal"] != len(results) or report["nonempty"] != len(results):
            raise ValueError("存在 SQL 不一致或空结果，参阅 artifacts/marketing-trial/mysql-verification.json")
        return report
    finally:
        await engine.dispose()


def score_answer(gold, actual):
    status = actual.get("status") == gold["expected_status"]
    sources = set(actual.get("sources", []))
    if gold["expected_status"] == "located":
        correct = status and sources == set(gold["sources"]) and actual.get("kind") == gold["kind"]
    elif gold["expected_status"] == "ambiguous":
        alternatives = {tuple(sorted(set(c.get("sources", [])))) for c in actual.get("candidates", [])}
        correct = status and not sources and alternatives == {tuple(sorted(a)) for a in gold["alternatives"]}
    else:
        correct = status and not sources and not actual.get("candidates")
    return {"correct": bool(correct), "status_correct": status,
            "formula_scope_verified": False if gold.get("kind") == "calculated" else None}


def evaluate(client, questions, gold, snapshot_id=None):
    """Only field names and a frozen snapshot ID leave this process."""
    if not snapshot_id:
        response = client.get("/api/v1/modeling/active")
        response.raise_for_status()
        active = response.json()
        if not active or not active.get("id"):
            raise ValueError("请先在平台完成建模、校验并采用模型，再运行评测")
        snapshot_id = active["id"]
    by_id = {a["id"]: a for a in gold}
    if set(by_id) != {q["id"] for q in questions} or len(by_id) != len(questions):
        raise ValueError("问题和答案 ID 不一致或存在重复")
    results = []
    for question in questions:
        try:
            response = client.post("/api/v1/modeling/trace",
                                   json={"fields": [question["field"]], "snapshot_id": snapshot_id})
            response.raise_for_status()
            payload = response.json()
            if payload.get("snapshot_id") != snapshot_id or len(payload.get("results", [])) != 1:
                raise ValueError("返回的快照或结果数量不符")
            actual = payload["results"][0]
            if actual.get("field") != question["field"]:
                raise ValueError("返回的字段不符")
            result = {**score_answer(by_id[question["id"]], actual), "actual": actual}
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            result = {"correct": False, "status_correct": False, "actual": {"status": "request_failed"},
                      "formula_scope_verified": False if question["category"] == "calculated" else None}
        results.append({"id": question["id"], "category": question["category"], **result})
    categories = defaultdict(lambda: {"correct": 0, "total": 0})
    for result in results:
        categories[result["category"]]["total"] += 1
        categories[result["category"]]["correct"] += int(result["correct"])
    correct = sum(r["correct"] for r in results)
    return {"snapshot_id": snapshot_id, "mode": "field_only_no_page_context",
            "total": len(results), "correct": correct, "source_status_accuracy": correct / len(results),
            "categories": dict(categories), "formula_scope_manual_review": sum(q["category"] == "calculated" for q in questions),
            "results": results}


def save_report(name, report):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
    print(f"报告：{path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install-mysql", "verify-mysql", "evaluate"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--snapshot-id")
    args = parser.parse_args()
    if args.command == "install-mysql":
        report = asyncio.run(install_mysql())
        print(f"已建立 16 张源表、37 个视图，载入 {report['row_count']} 行合成数据。")
    elif args.command == "verify-mysql":
        report = asyncio.run(verify_mysql())
        print(f"已核对 {report['sql_equal']}/{report['checked_answers']} 道题的 SQL，执行 {report['hot_queries_executed']} 条热点查询。")
    else:
        manifest = check_package()
        if httpx.URL(args.base_url).host not in {"127.0.0.1", "localhost", "::1"}:
            parser.error("评测脚本默认只允许本机平台")
        with httpx.Client(base_url=args.base_url, timeout=90, trust_env=False) as client:
            report = evaluate(client, read_json(PACKAGE / "evaluation/questions.json"),
                              read_json(PACKAGE / "evaluation/gold/answers.json"), args.snapshot_id)
        report.update(dataset=manifest["dataset"], questions_sha256=manifest["questions_sha256"],
                      answers_sha256=manifest["answers_sha256"], evaluated_at=datetime.now(timezone.utc).isoformat())
        save_report("evaluation-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json", report)
        print(f"字段来源/状态得分：{report['correct']}/{report['total']}；计算口径另有 20 题需人工核对。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, httpx.HTTPError) as error:
        raise SystemExit(str(error)) from None
