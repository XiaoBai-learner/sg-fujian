import importlib.util
import json
from collections import Counter
from pathlib import Path

import httpx
import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[3]
TRIAL = ROOT / "trials/marketing_v1"


def load_tool(name):
    path = TRIAL / f"{name}.py"
    assert path.exists(), f"缺少试用工具：{path.name}"
    spec = importlib.util.spec_from_file_location(f"marketing_trial_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_trial_has_100_independent_answers_and_non_destructive_inputs(tmp_path):
    tool = load_tool("build")
    tool.build(tmp_path)
    questions = json.loads((tmp_path / "evaluation/questions.json").read_text())
    gold = json.loads((tmp_path / "evaluation/gold/answers.json").read_text())
    assert len(questions) == len(gold) == 100
    assert len({q["id"] for q in questions}) == 100
    assert Counter(q["category"] for q in questions) == {
        "direct": 60, "calculated": 20, "ambiguous": 10, "not_found": 10,
    }
    assert all("sources" not in q and "expected_status" not in q for q in questions)
    ddl = (tmp_path / "inputs/01_source_ddl.sql").read_text()
    tables = [t for t in sqlglot.parse(ddl, read="mysql") if isinstance(t, exp.Create)]
    assert len(tables) == 16
    assert all(t.kind == "TABLE" for t in tables)
    assert "DROP " not in ddl.upper()
    assert {t.this.this.db for t in tables} == {
        "sgtrace_trial_yx186", "sgtrace_trial_cjxt", "sgtrace_trial_kf95598",
    }
    answer = next(a for a in gold if a.get("target") == "dwd_yx_df_ysmx.ysje")
    assert answer["sources"] == ["sgtrace_trial_yx186.A_RCVBL_FLOW.RCVBL_AMT"]
    calculated = next(a for a in gold if a.get("target") == "dwd_yx_cbsz.cjdl")
    assert set(calculated["sources"]) == {
        "sgtrace_trial_yx186.R_READ.LAST_READ",
        "sgtrace_trial_yx186.R_READ.THIS_READ",
        "sgtrace_trial_yx186.D_METER.T_FACTOR",
    }
    for answer in gold:
        if answer["expected_status"] == "located":
            assert answer["lineage_paths"] and answer["verification_sql"]
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert len(manifest["hot_queries"]) == 22
    assert all(item["exec_count_90d"] > 0 for item in manifest["hot_queries"])
    assert all(b"\r\n" not in path.read_bytes() for path in (tmp_path / "evaluation").rglob("*.csv"))
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    tool.build(tmp_path)
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_scoring_requires_exact_sources_and_complete_ambiguity():
    score = load_tool("run").score_answer
    gold = {"expected_status": "located", "kind": "calculated", "sources": ["db.T.A", "db.T.B"]}
    assert not score(gold, {"status": "located", "sources": ["db.T.A"], "kind": "calculated"})["correct"]
    result = score(gold, {"status": "located", "sources": ["db.T.B", "db.T.A"], "kind": "calculated"})
    assert result["correct"] and result["formula_scope_verified"] is False
    assert not score(gold, {"status": "located", "sources": ["db.T.A", "db.T.B"], "kind": "direct"})["correct"]
    ambiguous = {"expected_status": "ambiguous", "alternatives": [["db.T.A"], ["db.X.A"]]}
    assert not score(ambiguous, {"status": "ambiguous", "sources": [], "candidates": []})["correct"]
    assert score(ambiguous, {"status": "ambiguous", "sources": [], "candidates": [
        {"sources": ["db.T.A"]}, {"sources": ["db.X.A"]},
    ]})["correct"]
    assert not score({"expected_status": "not_found"}, {"status": "not_found", "sources": ["db.T.A"]})["correct"]


def test_evaluator_pins_snapshot_and_never_sends_answers():
    tool = load_tool("run")
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"id": "frozen-snapshot", "version": 3})
        body = json.loads(request.content)
        assert body == {"fields": ["应收金额"], "snapshot_id": "frozen-snapshot"}
        return httpx.Response(200, json={"snapshot_id": "frozen-snapshot", "results": [{
            "field": "应收金额", "status": "located", "kind": "direct", "sources": ["db.T.A"],
        }]})

    with httpx.Client(transport=httpx.MockTransport(handle), base_url="http://test") as client:
        result = tool.evaluate(client, [
            {"id": "M001", "field": "应收金额", "category": "direct"},
            {"id": "M002", "field": "应收金额", "category": "direct"},
        ], [
            {"id": "M001", "expected_status": "located", "kind": "direct", "sources": ["db.T.A"]},
            {"id": "M002", "expected_status": "located", "kind": "direct", "sources": ["db.T.A"]},
        ])
    assert result["snapshot_id"] == "frozen-snapshot"
    assert result["correct"] == result["total"] == 2
    assert len([r for r in requests if r.method == "GET"]) == 1


def test_mysql_setup_refuses_existing_database_without_writing():
    tool = load_tool("run")
    assert tool.SCHEMAS == (
        "sgtrace_trial_yx186", "sgtrace_trial_cjxt", "sgtrace_trial_kf95598", "sgtrace_trial_platform",
    )
    assert not tool.can_install({"yx186", "sgtrace_trial_cjxt"})
    assert tool.can_install({"yx186", "sgtrace_product"})


def test_building_inputs_does_not_read_gold(tmp_path, monkeypatch):
    tool = load_tool("build")
    original_open = Path.open

    def checked_open(path, *args, **kwargs):
        assert "/data/gold/" not in str(path), "建模输入不能读取标准答案"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    sources, _, _, _, _ = tool.build_inputs(tmp_path)
    assert len(sources) == 16
    assert len(list((tmp_path / "inputs").glob("*.sql"))) == 4


def test_evaluator_counts_failed_requests_and_missing_context_as_failures():
    tool = load_tool("run")

    def handle(request):
        field = json.loads(request.content)["fields"][0]
        if field == "超时字段":
            raise httpx.ReadTimeout("test", request=request)
        return httpx.Response(200, json={"snapshot_id": "snapshot", "results": [
            {"field": field, "status": "ambiguous", "sources": [], "candidates": [
                {"sources": ["db.A.NAME"]}, {"sources": ["db.B.NAME"]},
            ]},
        ]})

    questions = [{"id": "M001", "field": "超时字段", "category": "direct"},
                 {"id": "M002", "field": "名称", "category": "direct"}]
    gold = [{"id": q["id"], "expected_status": "located", "kind": "direct", "sources": ["db.A.NAME"]}
            for q in questions]
    with httpx.Client(transport=httpx.MockTransport(handle), base_url="http://test") as client:
        result = tool.evaluate(client, questions, gold, "snapshot")
    assert result["total"] == 2 and result["correct"] == 0
    assert result["categories"]["direct"] == {"correct": 0, "total": 2}


def test_evaluator_logs_in_and_uses_session_cookie_and_csrf():
    tool = load_tool("run")

    def handle(request):
        if request.url.path.endswith("/auth/login"):
            assert request.headers["x-requested-with"] == "SGTrace"
            assert json.loads(request.content) == {"username": "tester", "password": "trial-password"}
            return httpx.Response(200, json={"csrf_token": "csrf-test"},
                                  headers={"Set-Cookie": "sgtrace_session=cookie-test; Path=/; HttpOnly"})
        assert request.headers["x-csrf-token"] == "csrf-test"
        assert "cookie-test" in request.headers["cookie"]
        return httpx.Response(204)

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
        tool.authenticate(client, "tester", "trial-password")
        assert client.post("/api/v1/auth/logout").status_code == 204
