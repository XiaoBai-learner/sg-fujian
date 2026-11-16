"""评测：用 data/gold/answers.csv（标准答案）给 20 个需求、90 个字段打分。

指标
  strict   预测源字段集合 == 答案 source_columns
  lenient  预测与 (source_columns ∪ acceptable_equivalents) 有交集，且没有答案之外的字段
  abstain  标记待确认的比例（待确认不计为答对）
分组：derivation（direct/derived/aggregated）、context_level（正常/低）、页面类型（中台/源系统）

对照组
  baseline_keyword  只用 DDL 列注释做字面匹配（不用本体、同义词、血缘、值校验）
  消融              分别去掉 同义词 / 值校验 / 中台血缘路线
"""
import csv
import json
from collections import defaultdict

from .config import DATA, INPUTS, SOURCE_DBS
from .qa import Options, QAEngine
from .text import strip


def load_requests(folder="requests"):
    idx = {}
    with open(INPUTS / folder / "_index.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            idx[r["request_id"]] = r
    out = []
    for p in sorted((INPUTS / folder).glob("[A-Z]*.json")):
        req = json.loads(p.read_text(encoding="utf-8"))
        req["context_level"] = idx.get(req["request_id"], {}).get("context_level", "")
        out.append(req)
    return out


def load_gold(name="answers.csv"):
    gold = {}
    with open(DATA / "gold" / name, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gold[(r["request_id"], r["field_label"])] = r
    return gold


def _score(pred, g, abstained):
    truth = set(filter(None, g["source_columns"].split(";")))
    eq = set(filter(None, g["acceptable_equivalents"].split(";")))
    p = set(pred)
    strict = (not abstained) and p == truth
    lenient = (not abstained) and bool(p) and bool(p & (truth | eq)) and not (p - truth - eq)
    return strict, lenient


def _aggregate(rows):
    def stat(items):
        n = len(items)
        if not n:
            return {"n": 0}
        return {"n": n, "strict": round(sum(r["strict"] for r in items) / n, 3),
                "lenient": round(sum(r["lenient"] for r in items) / n, 3),
                "abstain": round(sum(r["abstained"] for r in items) / n, 3)}
    groups = defaultdict(list)
    for r in rows:
        groups[("derivation", r["derivation"])].append(r)
        groups[("context", r["context_level"])].append(r)
        groups[("page", "源系统页" if not r["gold_platform_column"] else "中台页")].append(r)
    return {"overall": stat(rows),
            "by_group": {f"{k}:{v}": stat(items) for (k, v), items in sorted(groups.items())}}


def run_engine(engine, requests, gold):
    rows = []
    for req in requests:
        res = engine.answer_screenshot(req["screenshot_ocr"], req["asked_fields"])
        for f in res["fields"]:
            g = gold.get((req["request_id"], f["label"]))
            if g is None:
                continue
            pred = [s["column"] for s in f["sources"]]
            abstained = f["status"] != "ok"
            strict, lenient = _score(pred, g, abstained)
            rows.append({"request_id": req["request_id"], "label": f["label"], "predicted": pred,
                         "expected": g["source_columns"].split(";"), "platform_predicted": f["platform_column"],
                         "gold_platform_column": g["platform_column"], "route": f["route"],
                         "confidence": f["confidence"], "derivation": g["derivation"],
                         "context_level": req["context_level"], "strict": strict, "lenient": lenient,
                         "abstained": abstained})
    return rows


def baseline_keyword(meta, requests, gold):
    """只用源表 DDL 列注释做字面包含匹配，取第一个命中。"""
    cols = []
    for db in SOURCE_DBS:
        for t in meta.get(db, {}).values():
            for c in t.columns:
                if c.comment:
                    cols.append((f"{t.qname}.{c.name}", strip(c.comment)))
    rows = []
    for req in requests:
        for label in req["asked_fields"]:
            g = gold.get((req["request_id"], label))
            if g is None:
                continue
            lab = strip(label)
            hit = next((q for q, cm in cols if cm == lab), None) or \
                next((q for q, cm in cols if lab in cm or cm in lab), None)
            pred = [hit] if hit else []
            strict, lenient = _score(pred, g, not hit)
            rows.append({"derivation": g["derivation"], "context_level": req["context_level"],
                         "gold_platform_column": g["platform_column"], "strict": strict,
                         "lenient": lenient, "abstained": not hit})
    return rows


def evaluate(build, semantic, evidence, evidence_no_tasks=None, ablations=True):
    requests, gold = load_requests(), load_gold()
    main = QAEngine(build, semantic, evidence)
    rows = run_engine(main, requests, gold)
    report = {"system": _aggregate(rows), "rows": rows,
              "baseline_keyword": _aggregate(baseline_keyword(build.meta, requests, gold))}
    if ablations:
        abl = {}
        for name, opt in (("no_synonyms", Options(synonyms=False)),
                          ("no_value_check", Options(value_check=False)),
                          ("no_platform_lineage", Options(platform=False))):
            eng = QAEngine(build, semantic, evidence, values=main.values, options=opt)
            abl[name] = _aggregate(run_engine(eng, requests, gold))["overall"]
        if evidence_no_tasks is not None:
            eng = QAEngine(build, semantic, evidence_no_tasks, values=main.values)
            abl["export_lineage_only"] = _aggregate(run_engine(eng, requests, gold))["overall"]
        report["ablations"] = abl
    # 留出集：规则调优期间未使用的页面与新叫法，衡量是否对 90 个开发集字段过拟合
    h_req, h_gold = load_requests("requests_holdout"), load_gold("answers_holdout.csv")
    h_rows = run_engine(main, h_req, h_gold)
    report["holdout"] = {**_aggregate(h_rows), "rows": h_rows,
                         "baseline_keyword": _aggregate(baseline_keyword(build.meta, h_req, h_gold))["overall"]}
    return report
