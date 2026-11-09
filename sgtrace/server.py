"""演示服务：构建本体与数据管道映射、展示本体、字段溯源问答。

启动：.venv/bin/python -m sgtrace.server  （默认只监听 127.0.0.1:8765）
注意：本服务没有鉴权，只用于本机演示，不要改成监听 0.0.0.0 或暴露到内网。
"""
import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import metadata, pipeline, wing
from .config import ARTIFACTS, INPUTS, SANDBOX, WEB, mysql_config
from .qa import QAEngine

app = FastAPI(title="sgtrace 字段溯源 PoC", docs_url="/api/docs", openapi_url="/api/openapi.json")
_lock = threading.Lock()
_state = {"result": None, "engine": None}

ARTIFACT_FILES = {"ontology.ttl": "text/turtle", "mapping.r2rml.ttl": "text/turtle",
                  "wing_model.json": "application/json", "wing_pipeline.json": "application/json",
                  "fact_plane_snapshots.json": "application/json", "build_report.json": "application/json"}


class BuildRequest(BaseModel):
    source: str = Field("auto", pattern="^(auto|mysql|ddl)$")
    execute_r2rml: bool = True
    evaluate: bool = True


class Question(BaseModel):
    question: str = Field(..., min_length=1, max_length=200)


class ScreenshotQuestion(BaseModel):
    ocr: str = Field(..., min_length=1, max_length=20000)
    fields: list[str] = Field(..., min_length=1, max_length=40)


def _engine():
    if _state["engine"] is None:
        with _lock:
            if _state["engine"] is None:
                _set(pipeline.run(execute_r2rml=False, run_eval=False, write=False))
    return _state["engine"]


def _set(result):
    _state["result"] = result
    _state["engine"] = QAEngine(result.build, result.semantic, result.evidence)


@app.get("/api/status")
def status():
    cfg = mysql_config()
    mysql = {"configured": cfg is not None, "target": cfg.display if cfg else "", "connected": False,
             "databases": {}}
    if cfg:
        try:
            conn = metadata.connect()
            with conn.cursor() as cur:
                cur.execute("SELECT TABLE_SCHEMA, COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA IN "
                            "(%s, %s, %s, %s) GROUP BY TABLE_SCHEMA", metadata.ALL_DBS)
                mysql["databases"] = dict(cur.fetchall())
            conn.close()
            mysql["connected"] = True
        except Exception as e:  # noqa: BLE001
            mysql["error"] = type(e).__name__ + ": " + str(e)[:200]
    r = _state["result"]
    return {"ontowing": wing.info(), "mysql": mysql,
            "sandbox": all((SANDBOX / f"{d}.db").exists() for d in ("platform", "yx186", "cjxt", "kf95598")),
            "built": r is not None, "summary": r.build.summary() if r else None,
            "artifacts": sorted(p.name for p in ARTIFACTS.glob("*") if p.name in ARTIFACT_FILES)}


@app.post("/api/mysql/init")
def mysql_init():
    if mysql_config() is None:
        raise HTTPException(400, "未配置 MySQL：在项目根目录 .env 中设置 MYSQL_USER / MYSQL_PASSWORD")
    try:
        created = metadata.load_ddl_into_mysql()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"建库失败：{type(e).__name__}: {str(e)[:300]}") from None
    return {"created_tables": created}


@app.post("/api/build")
def build(req: BuildRequest):
    with _lock:
        try:
            result = pipeline.run(req.source, execute_r2rml=req.execute_r2rml, run_eval=req.evaluate)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"构建失败：{type(e).__name__}: {str(e)[:500]}") from None
        _set(result)
    rep = result.report
    ev = rep.get("evaluation")
    return {"steps": rep["steps"], "summary": rep["summary"], "decisions": rep["decisions"],
            "relations": rep["relations"], "ontowing": rep["ontowing"],
            "wing_validation": {k: {"valid": v["valid"], "checks": v.get("checks"),
                                    "diagnostics": v.get("diagnostics", [])[:20]}
                                for k, v in rep["wing_validation"].items()},
            "r2rml_execution": rep["r2rml_execution"],
            "evaluation": None if ev is None else {k: ev[k] for k in ("system", "baseline_keyword", "ablations")}
            | {"holdout": {k: ev["holdout"][k] for k in ("overall", "by_group", "baseline_keyword")},
               "misses": [r for r in ev["rows"] + ev["holdout"]["rows"] if not r["strict"]]}}


@app.get("/api/ontology")
def ontology():
    eng = _engine()
    r = _state["result"]
    g = r.semantic.graph()
    concept_meta = {c["id"]: c for c in r.build.model["concepts"]}
    for n in g["nodes"]:
        c = concept_meta.get(n["id"], {})
        n["description"] = c.get("description", "")
        n["top_category"] = c.get("top_category")
    return {**g, "summary": r.build.summary(), "ready": eng is not None}


@app.post("/api/ask")
def ask(q: Question):
    return _engine().answer_question(q.question)


@app.post("/api/ask/screenshot")
def ask_screenshot(q: ScreenshotQuestion):
    return _engine().answer_screenshot(q.ocr, q.fields)


@app.get("/api/samples")
def samples():
    out = []
    for folder in ("requests", "requests_holdout"):
        for p in sorted((INPUTS / folder).glob("[A-Z]*.json")):
            r = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": r["request_id"], "set": "留出集" if folder.endswith("holdout") else "开发集",
                        "from_dept": r["from_dept"], "subject": r["email_subject"], "body": r["email_body"],
                        "ocr": r["screenshot_ocr"], "fields": r["asked_fields"]})
    return out


@app.get("/api/artifacts/{name}")
def artifact(name: str):
    if name not in ARTIFACT_FILES:
        raise HTTPException(404, "没有这个产物")
    path = ARTIFACTS / name
    if not path.exists():
        raise HTTPException(404, "尚未构建，请先执行“构建本体”")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type=ARTIFACT_FILES[name] + "; charset=utf-8")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")


def main():
    import uvicorn
    host = os.environ.get("SGTRACE_HOST", "127.0.0.1")
    port = int(os.environ.get("SGTRACE_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
