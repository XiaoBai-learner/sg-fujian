"""构建流水线：元数据 → 证据 → 本体/映射/规则（OntoWing 校验与导出）→ R2RML 实跑 → 规则推理 → 语义索引 → 评测。

产物写到 artifacts/：
  ontology.ttl            OntoWing 导出的 OWL（owl-core/1）
  mapping.r2rml.ttl       OntoWing 导出的 R2RML（r2rml-record/1）
  rules.ttl               OntoWing 导出的 SWRL 规则（swrl-simple/1）
  wing_rules.json         OntoWing 规则编辑器 JSON（wing-rules-editor/2，含约束）
  wing_model.json         OntoWing 模型编辑器 JSON（wing-model-editor/1）
  wing_pipeline.json      OntoWing 数据管道编辑器 JSON（wing-pipeline-editor/2）
  fact_plane_snapshots.json  校验用的表字典快照
  build_report.json       各步骤日志、校验报告、R2RML 实跑结果、评测结果
"""
import json
import time
from dataclasses import dataclass

from . import metadata, reason, verify, wing
from .builder import OntologyBuild
from .config import ARTIFACTS
from .evaluate import evaluate
from .evidence import Evidence
from .semantic import SemanticIndex


@dataclass
class BuildResult:
    build: OntologyBuild
    evidence: Evidence
    semantic: SemanticIndex
    ontology_ttl: str
    mapping_ttl: str
    rules_ttl: str
    report: dict


def _step(steps, name, fn):
    t = time.time()
    try:
        out = fn()
        steps.append({"step": name, "ok": True, "seconds": round(time.time() - t, 2)})
        return out
    except Exception as e:
        steps.append({"step": name, "ok": False, "seconds": round(time.time() - t, 2), "error": str(e)[:500]})
        raise


def run(source="auto", execute_r2rml=True, run_eval=True, write=True):
    steps = []
    meta, used = _step(steps, "读取表结构元数据", lambda: metadata.load(source))
    steps[-1]["detail"] = {"source": used, "tables": {db: len(t) for db, t in meta.items()}}

    ev = _step(steps, "采集证据（血缘 / 任务 SQL / 热点 SQL）", lambda: Evidence(meta))
    steps[-1]["detail"] = ev.stats

    b = _step(steps, "生成领域本体与数据管道映射", lambda: OntologyBuild(meta, ev, used))
    steps[-1]["detail"] = {"log": b.log, **b.summary()}

    model_report = _step(steps, "OntoWing 校验本体（wing-model-editor/1）", lambda: wing.validate_model(b.model))
    steps[-1]["detail"] = _brief(model_report)
    pipe_report = _step(steps, "OntoWing 校验数据管道映射（wing-pipeline-editor/2）",
                        lambda: wing.validate_pipeline(b.pipeline, b.model, b.snapshots))
    steps[-1]["detail"] = _brief(pipe_report)
    rules_report = _step(steps, "OntoWing 校验规则与约束（wing-rules-editor/2）",
                         lambda: wing.validate_rules(b.rules, b.model))
    steps[-1]["detail"] = _brief(rules_report)
    if not model_report["valid"] or not pipe_report["valid"] or not rules_report["valid"]:
        raise RuntimeError("OntoWing 校验未通过，见 build_report.json")

    onto, _, oprof, oloss = _step(steps, "OntoWing 导出 ontology.ttl", lambda: wing.render("model", b.model))
    steps[-1]["detail"] = {"profile": oprof, "export_losses": oloss, "bytes": len(onto.encode())}
    mapping, _, mprof, mloss = _step(steps, "OntoWing 导出 mapping.ttl（R2RML）",
                                     lambda: wing.render("pipeline", b.pipeline, b.model))
    steps[-1]["detail"] = {"profile": mprof, "export_losses": mloss, "bytes": len(mapping.encode())}

    rules_ttl, _, rprof, rloss = _step(steps, "OntoWing 导出 rules.ttl（SWRL）", lambda: wing.render("rules", b.rules, b.model))
    steps[-1]["detail"] = {"profile": rprof, "export_losses": rloss,
                           "exported_rules": rules_ttl.count("rule:source_code")}

    r2rml, reasoning = None, None
    if execute_r2rml:
        r2rml = _step(steps, "Morph-KGC 在沙箱数据上执行 R2RML", lambda: verify.check(mapping, b.pipeline, b.model))
        graph = r2rml.pop("graph")
        steps[-1]["detail"] = {k: v for k, v in r2rml.items() if k != "relations"}
        reasoning = _step(steps, "在实例图上执行 SWRL 规则并检查约束（对照独立 SQL 口径）",
                          lambda: reason.run(graph, onto, rules_ttl, b.rules, b.rule_meta, b.model))
        steps[-1]["detail"] = {"passed": reasoning["passed"], "rounds": reasoning["rounds"],
                               "rules": [(x["name"], x["inferred"], x["sql_check"]) for x in reasoning["rules"]],
                               "constraint_violations": sum(c["violations"] for c in reasoning["constraints"])}
        del graph

    sem = _step(steps, "从导出文件构建语义索引", lambda: SemanticIndex(onto, mapping, b.pipeline, rules_ttl, b.rule_meta))
    steps[-1]["detail"] = {"concepts": len(sem.concepts), "predicates": len(sem.preds),
                           "mapped_columns": len(sem.column_pred)}

    ev_export_only = Evidence(meta, parse_tasks=False) if run_eval else None
    evaluation = None
    if run_eval:
        evaluation = _step(steps, "评测（20 个需求 / 90 个字段）",
                           lambda: evaluate(b, sem, ev, ev_export_only))

        steps[-1]["detail"] = {"system": evaluation["system"]["overall"],
                               "baseline_keyword": evaluation["baseline_keyword"]["overall"],
                               "holdout": evaluation["holdout"]["overall"],
                               "holdout_baseline": evaluation["holdout"]["baseline_keyword"]}

    report = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "ontowing": wing.info(), "steps": steps,
              "summary": b.summary(), "decisions": b.decisions, "relations": [
                  {k: r[k] for k in ("id", "name", "child", "child_col", "parent", "parent_col", "provenance")}
                  for r in b.relations],
              "rules": b.rule_meta,
              "wing_validation": {"model": model_report, "pipeline": pipe_report, "rules": rules_report},
              "r2rml_execution": r2rml, "reasoning": reasoning, "evaluation": evaluation}
    if write:
        ARTIFACTS.mkdir(exist_ok=True)
        (ARTIFACTS / "ontology.ttl").write_text(onto, encoding="utf-8")
        (ARTIFACTS / "mapping.r2rml.ttl").write_text(mapping, encoding="utf-8")
        (ARTIFACTS / "rules.ttl").write_text(rules_ttl, encoding="utf-8")
        for name, obj in (("wing_model.json", b.model), ("wing_pipeline.json", b.pipeline), ("wing_rules.json", b.rules),
                          ("fact_plane_snapshots.json", b.snapshots), ("build_report.json", report)):
            (ARTIFACTS / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=list),
                                          encoding="utf-8")
    return BuildResult(b, ev, sem, onto, mapping, rules_ttl, report)


def _brief(r):
    return {"valid": r["valid"], "checks": r.get("checks"),
            "diagnostics": [{k: d.get(k) for k in ("code", "severity", "path", "message")}
                            for d in r.get("diagnostics", [])][:50]}
