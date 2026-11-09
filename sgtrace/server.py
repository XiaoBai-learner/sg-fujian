"""演示服务：构建本体与数据管道映射、展示本体、字段溯源问答。

本机模式（默认）：.venv/bin/python -m sgtrace.server
  只监听 127.0.0.1:8765，无鉴权，可在页面上执行 MySQL 建库。

公网模式：SGTRACE_PUBLIC=1 SGTRACE_PORT=8766 .venv/bin/python -m sgtrace.server
  仍只监听 127.0.0.1，由 cloudflared 隧道对外提供 HTTPS；在本机模式基础上：
  - 所有页面和接口都要求 HTTP Basic 认证（用户名 demo，口令在 .public_token，首次启动随机生成）
  - 认证失败按来源 IP 限流（10 分钟 20 次）
  - 禁用 MySQL 建库（DROP/CREATE）接口、接口文档
  - 构建接口串行执行并限频（60 秒一次）
  - 状态接口不返回本机路径、MySQL 账号与内部错误信息
  - 加安全响应头（CSP、禁止被嵌入、nosniff 等）
"""
import base64
import binascii
import hmac
import json
import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import metadata, pipeline, wing
from .config import ARTIFACTS, INPUTS, ROOT, SANDBOX, WEB, mysql_config
from .qa import QAEngine

log = logging.getLogger("sgtrace")

app = FastAPI(title="sgtrace 字段溯源 PoC", docs_url="/api/docs", openapi_url="/api/openapi.json")
_lock = threading.Lock()
_state = {"result": None, "engine": None, "last_build": 0.0}

ARTIFACT_FILES = {"ontology.ttl": "text/turtle", "mapping.r2rml.ttl": "text/turtle", "rules.ttl": "text/turtle",
                  "wing_rules.json": "application/json",
                  "wing_model.json": "application/json", "wing_pipeline.json": "application/json",
                  "fact_plane_snapshots.json": "application/json", "build_report.json": "application/json"}

PUBLIC_USER = "demo"
TOKEN_FILE = ROOT / ".public_token"
BUILD_INTERVAL = 60
AUTH_FAIL_LIMIT, AUTH_FAIL_WINDOW = 20, 600
_auth_fails = defaultdict(deque)
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                               "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def public_mode():
    return os.environ.get("SGTRACE_PUBLIC") == "1"


def public_token():
    """读取或生成公网访问口令（文件权限 600，已 gitignore）。"""
    env = os.environ.get("SGTRACE_PUBLIC_TOKEN")
    if env:
        return env
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(18)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token + "\n")
    return token


def _client_ip(request: Request):
    # 经 cloudflared 转发时真实来源在 CF-Connecting-IP；本机直连时用 socket 地址
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")


def _authorized(request: Request):
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        return False
    try:
        user, _, pwd = base64.b64decode(header[6:], validate=True).decode("utf-8").partition(":")
    except (binascii.Error, UnicodeDecodeError):
        return False
    ok_user = hmac.compare_digest(user.encode(), PUBLIC_USER.encode())
    ok_pwd = hmac.compare_digest(pwd.encode(), public_token().encode())
    return ok_user and ok_pwd


@app.middleware("http")
async def guard(request: Request, call_next):
    if public_mode():
        ip, now = _client_ip(request), time.time()
        fails = _auth_fails[ip]
        while fails and now - fails[0] > AUTH_FAIL_WINDOW:
            fails.popleft()
        if len(fails) >= AUTH_FAIL_LIMIT:
            return JSONResponse({"detail": "认证失败次数过多，请稍后再试"}, status_code=429, headers=SECURITY_HEADERS)
        if not _authorized(request):
            if request.headers.get("authorization"):
                fails.append(now)
            return Response("需要认证", status_code=401, media_type="text/plain; charset=utf-8",
                            headers={"WWW-Authenticate": 'Basic realm="sgtrace", charset="UTF-8"', **SECURITY_HEADERS})
        if request.url.path in ("/api/docs", "/api/openapi.json", "/api/docs/oauth2-redirect"):
            return JSONResponse({"detail": "Not Found"}, status_code=404, headers=SECURITY_HEADERS)
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


def _fail(status, public_msg, exc):
    """公网模式只返回概括信息，细节写服务端日志。"""
    log.exception("%s", public_msg)
    detail = public_msg if public_mode() else f"{public_msg}：{type(exc).__name__}: {str(exc)[:500]}"
    raise HTTPException(status, detail) from None


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
    pub = public_mode()
    mysql = {"configured": cfg is not None, "target": "" if pub else (cfg.display if cfg else ""),
             "connected": False, "databases": {}}
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
            if not pub:
                mysql["error"] = type(e).__name__ + ": " + str(e)[:200]
    w = wing.info()
    if pub:
        w = {"available": w["available"], "commit": w["commit"], "backend": "", "error": ""}
    r = _state["result"]
    return {"public": pub, "ontowing": w, "mysql": mysql,
            "sandbox": all((SANDBOX / f"{d}.db").exists() for d in ("platform", "yx186", "cjxt", "kf95598")),
            "built": r is not None, "summary": r.build.summary() if r else None,
            "artifacts": sorted(p.name for p in ARTIFACTS.glob("*") if p.name in ARTIFACT_FILES)}


@app.post("/api/mysql/init")
def mysql_init():
    if public_mode():
        raise HTTPException(403, "公网模式禁用建库")
    if mysql_config() is None:
        raise HTTPException(400, "未配置 MySQL：在项目根目录 .env 中设置 MYSQL_USER / MYSQL_PASSWORD")
    try:
        created = metadata.load_ddl_into_mysql()
    except Exception as e:  # noqa: BLE001
        _fail(500, "建库失败", e)
    return {"created_tables": created}


@app.post("/api/build")
def build(req: BuildRequest):
    if public_mode():
        wait = BUILD_INTERVAL - (time.time() - _state["last_build"])
        if wait > 0:
            raise HTTPException(429, f"构建过于频繁，请 {int(wait) + 1} 秒后再试")
        if not _lock.acquire(blocking=False):
            raise HTTPException(429, "已有构建在进行中，请稍后再试")
    else:
        _lock.acquire()
    try:
        _state["last_build"] = time.time()
        try:
            result = pipeline.run(req.source, execute_r2rml=req.execute_r2rml, run_eval=req.evaluate)
        except Exception as e:  # noqa: BLE001
            _fail(500, "构建失败", e)
        _set(result)
    finally:
        _lock.release()
    rep = result.report
    ev = rep.get("evaluation")
    w = rep["ontowing"]
    if public_mode():
        w = {**w, "backend": ""}
    return {"steps": rep["steps"], "summary": rep["summary"], "decisions": rep["decisions"],
            "relations": rep["relations"], "ontowing": w,
            "wing_validation": {k: {"valid": v["valid"], "checks": v.get("checks"),
                                    "diagnostics": v.get("diagnostics", [])[:20]}
                                for k, v in rep["wing_validation"].items()},
            "r2rml_execution": rep["r2rml_execution"], "reasoning": rep.get("reasoning"), "rules": rep.get("rules"),
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
    logging.basicConfig(level=logging.INFO)
    host = os.environ.get("SGTRACE_HOST", "127.0.0.1")
    port = int(os.environ.get("SGTRACE_PORT", "8765"))
    if public_mode():
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise SystemExit("公网模式只允许监听本机地址，对外暴露请走 cloudflared 隧道")
        public_token()
        log.info("公网模式：Basic 认证用户 %s，口令见 %s", PUBLIC_USER, TOKEN_FILE)
    uvicorn.run(app, host=host, port=port, proxy_headers=False, server_header=False)


if __name__ == "__main__":
    main()
