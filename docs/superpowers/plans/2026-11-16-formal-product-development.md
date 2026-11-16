# 字段溯源工作台正式产品研发实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在用户确认的三模块工作台形态上，建设可持久化、可联调、可交付的字段溯源产品：数据源接入 → OntoWing 本体建模 → 基于本体与 R2RML 的字段溯源智能体。

**Architecture:** 正式前端 `frontend/` 负责统一工作台、材料选择、建模编辑和溯源结果；正式后端 `backend/` 负责三个业务模块、持久化、任务状态和 API。`reference/poc/` 只作为已验证算法、引擎适配和合成数据的迁移依据，不作为运行时入口。系统以“已采用模型快照”为查询边界，以材料身份、血缘证据和工具结果保证回答可复查。

**Tech Stack:** React 18 + TypeScript + Vite；FastAPI + Pydantic；SQLAlchemy 2.x Async + Alembic；MySQL 8+ 业务库；本地文件存储抽象（生产可替换对象存储）；OntoWing 纯领域模块；RDFLib、Morph-KGC、SQLGlot；数据库任务表 + worker 轮询；pytest、Node test、Playwright 或浏览器人工验收。

**Spec:** `docs/product.md`、`docs/architecture.html`、`AGENTS.md`、`product-demo/README.md`、`reference/poc/README.md`

## Global Constraints

- 只做营销域、福州试点；不新增第二业务领域，不做全域治理、码值翻译、OCR、业务取数 SQL 执行或客户主数据合并。
- 产品只保留数据源接入、OntoWing 本体建模、字段溯源智能体三个业务模块；所有用户使用同一套功能，不引入角色职责、审批队列、需求工单或复核工作台。
- 文档、接入 DDL、结构快照可以组成同一个建模输入集合；材料必须保留来源身份、解析状态和版本。
- 字段候选必须来自已采用 OWL + R2RML 语义索引；大模型只负责理解问题和选择工具，不能编写工具未返回的表名、字段名或血缘。
- 草稿与已采用快照隔离；采用前的编辑、生成结果和失败任务不能改变智能体当前查询结果。
- 实体键不能为可空列；关联 JOIN 必须完整覆盖父绑定键；属性只能映射到自身概念或祖先绑定；同一物理列不能映射冲突 datatype。
- 不保存明文数据库密码、LLM API key 或原始敏感数据行；材料正文、连接配置、问答结果按部署的密钥和访问边界保护。
- 新 HTTP 接口使用 `/api/v1/`，健康检查使用 `/api/healthz`；未实现的接口返回 404 或明确错误，禁止返回模拟成功。
- 正式应用不得自动读取 `reference/poc/data/gold`、自动执行 PoC 数据生成或导入 PoC 的全局运行状态。
- 本地服务默认只监听 `127.0.0.1`；部署、外部访问和密钥配置在业务闭环通过后单独验收。
- 每个任务先写失败测试，再写最小实现；每个阶段结束运行相关单测、集成测试和构建检查。

## Target Directory Contract

实现过程中只增加或修改以下正式目录；`product-demo/` 与 `reference/poc/` 只在明确迁移任务中读取和补测试。

```text
backend/
  pyproject.toml
  alembic.ini
  migrations/
  src/sgtrace_app/
    main.py
    config.py
    api/
      v1/
        router.py
        errors.py
    modules/
      sources/
      modeling/
      agent/
    domain/
      ids.py
      jobs.py
      snapshots.py
    integrations/
      ontowing/
      poc_engine/
      llm/
    infrastructure/
      db/
      storage/
      worker/
  tests/
    unit/
    integration/
    contract/
frontend/src/
  app/
  modules/sources/
  modules/modeling/
  modules/agent/
  shared/api/
  shared/components/
  shared/types/
```

## Delivery Milestones

| Milestone | 可验收结果 | 主要依赖 |
|---|---|---|
| M0 基础平台 | 正式前后端、迁移、配置、日志、健康检查、CI 检查链可运行 | 无 | **基础版本完成**
| M1 数据源闭环 | 用户可创建只读数据源、同步结构、上传材料、查看解析状态和血缘材料 | M0 | **DDL/本地材料第一版完成；真实连接与异步解析待补**
| M2 建模闭环 | 用户可从文档 + DDL 生成草稿、编辑本体/R2RML、校验并采用模型快照 | M1、OntoWing |
| M3 智能体闭环 | 用户可提问字段/OCR，获得原表字段、计算口径、证据和历史结果 | M2 |
| M4 工作台交付 | 正式前端替换 demo mock，三个模块可用同一 API 完整操作 | M1–M3 |
| M5 可部署交付 | 容器、迁移、备份、观测、权限和现场验收文档完成 | M4 |

---

### Task 1: 固定正式工程边界与开发检查

**Files:**

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `Makefile`
- Modify: `pytest.ini`
- Create: `.github/workflows/check.yml` 或仓库现有 CI 配置
- Test: `backend/tests/test_bootstrap.py`

**Interfaces:**

- Produces `make check`, `make check-web`, `make test` 三个稳定命令。
- Produces a CI check that runs typecheck, backend unit tests, frontend build, and demo regression without starting external services.

- [x] **Step 1: 把正式目录、PoC 目录、demo 目录和文档基线写入项目说明**

  README 必须明确：`frontend/` 和 `backend/` 是正式实现，`product-demo/` 是验收参照，`reference/poc/` 是迁移依据。写明正式业务尚未完成，避免后续把骨架当作已交付产品。

- [x] **Step 2: 为正式命令写一个失败检查**

  在 `backend/tests/test_bootstrap.py` 增加：

  ```python
  def test_formal_app_does_not_import_poc_runtime():
      import sys
      assert "reference/poc" not in ":".join(sys.path)
  ```

  运行 `make test`，确认测试在当前 import 配置下先失败或暴露路径问题，再修正测试环境。

- [x] **Step 3: 固定测试路径和忽略规则**

  让 pytest 发现 `backend/tests` 和 `reference/poc/tests`；确保 `node_modules/`、`dist/`、`artifacts/`、`reference/poc/data/sandbox/`、运行密钥和上传目录不会进入 Git。

- [x] **Step 4: 增加 CI 只读检查**

  CI 至少执行：

  ```bash
  python -m pytest backend/tests/unit backend/tests/contract -q
  npm --prefix frontend run build
  npm --prefix product-demo test
  npm --prefix product-demo run build
  git diff --check
  ```

  CI 不读取真实凭据，不连接客户数据库，不执行公网隧道。

- [x] **Step 5: 运行全部基础检查并提交**

  ```bash
  make check-web
  npm --prefix product-demo test
  npm --prefix product-demo run build
  git add README.md AGENTS.md Makefile pytest.ini backend/tests .github
  git commit -m "chore: fix formal development checks"
  ```

**Acceptance:** 新工程可以从干净环境识别正式入口、demo 参照和 PoC 参考；检查命令失败时能定位具体阶段。

---

### Task 2: 建立配置、数据库和任务基础设施

**Files:**

- Create: `backend/src/sgtrace_app/config.py`
- Create: `backend/src/sgtrace_app/api/v1/router.py`
- Create: `backend/src/sgtrace_app/api/v1/errors.py`
- Create: `backend/src/sgtrace_app/infrastructure/db/session.py`
- Create: `backend/src/sgtrace_app/infrastructure/db/models.py`
- Create: `backend/src/sgtrace_app/infrastructure/db/repositories.py`
- Create: `backend/src/sgtrace_app/domain/jobs.py`
- Create: `backend/src/sgtrace_app/infrastructure/worker/runner.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_initial.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/unit/test_config.py`
- Test: `backend/tests/integration/test_db_bootstrap.py`

**Interfaces:**

- `Settings.from_env() -> Settings` validates database URL, storage root, worker polling interval, maximum material size and allowed origins.
- `create_session_factory(settings) -> async_sessionmaker`.
- `JobRepository.enqueue(kind: str, payload: dict) -> Job`.
- `JobRepository.claim_next(worker_id: str) -> Job | None`.
- `JobRepository.complete(job_id, result_ref)`, `fail(job_id, code, detail)`, `cancel(job_id)`.
- All repositories return domain DTOs, not SQLAlchemy models.

- [x] **Step 1: Write configuration failure tests**

  Cover missing `DATABASE_URL`, invalid material size, unsupported storage scheme, and valid local test settings. Assert secrets are not included in `repr(Settings)` or health response.

- [x] **Step 2: Fix the formal API prefix before adding business routes**

  Change the three skeleton routers to use `/api/v1/sources`, `/api/v1/modeling` and `/api/v1/agent`. Keep `/api/healthz` and later `/api/readyz` outside the versioned business router. Register them through `api/v1/router.py`, so every later task adds endpoints to one explicit version boundary.

- [x] **Step 3: Write migration and job tests**

  Use a temporary MySQL-compatible database in integration tests. Assert `jobs` has `pending/running/succeeded/failed/cancelled` states, a lease timestamp, attempt count, idempotency key, error code, and result reference. Assert a second worker cannot claim an unexpired lease.

- [x] **Step 4: Implement settings and SQLAlchemy async session**

  Use SQLAlchemy 2.x AsyncEngine, explicit pool settings, `pool_pre_ping`, and `expire_on_commit=False`. Do not use Django ORM. Keep transactions in repositories and keep external calls outside transactions.

- [x] **Step 5: Implement initial schema and migration**

  Initial tables:

  - `workspaces(id, name, domain, created_at, updated_at)`
  - `users(id, external_subject, display_name, created_at)`
  - `workspace_members(workspace_id, user_id, created_at)` with one permission set
  - `jobs(id, kind, status, payload_json, result_ref, idempotency_key, lease_owner, lease_until, attempts, error_code, error_detail, created_at, updated_at)`
  - `audit_events(id, workspace_id, actor_id, event_type, object_type, object_id, payload_json, created_at)`

- [x] **Step 6: Implement worker claim protocol**

  `claim_next` must atomically select one pending job or reclaim an expired lease. Worker execution must check cancellation before each external phase, record progress, and never retry a job after an unknown external request without reconciliation.

- [x] **Step 7: Run migration and unit/integration tests**

  ```bash
  alembic upgrade head
  python -m pytest backend/tests/unit/test_config.py backend/tests/integration/test_db_bootstrap.py -q
  ```

- [x] **Step 8: Commit**

  ```bash
  git add backend/src/sgtrace_app/config.py backend/src/sgtrace_app/domain/jobs.py backend/src/sgtrace_app/infrastructure backend/migrations backend/alembic.ini backend/pyproject.toml backend/tests
  git commit -m "feat: add formal application foundation"
  ```

**Acceptance:** 正式服务可以在空数据库创建 schema；任务可以安全排队、领取、续租、完成、失败和取消；没有角色权限矩阵。

---

### Task 3: 建立材料与文件存储边界

**Files:**

- Create: `backend/src/sgtrace_app/infrastructure/storage/base.py`
- Create: `backend/src/sgtrace_app/infrastructure/storage/local.py`
- Create: `backend/src/sgtrace_app/modules/sources/materials/models.py`
- Create: `backend/src/sgtrace_app/modules/sources/materials/schemas.py`
- Create: `backend/src/sgtrace_app/modules/sources/materials/service.py`
- Create: `backend/migrations/versions/0002_materials.py`
- Test: `backend/tests/unit/test_material_validation.py`
- Test: `backend/tests/integration/test_material_lifecycle.py`

**Interfaces:**

- `Storage.put(stream, key, content_type) -> StoredObject(sha256, size_bytes, uri)`.
- `Storage.open(uri) -> BinaryIO`.
- `MaterialService.create_upload(workspace_id, actor_id, metadata) -> MaterialUpload`.
- `MaterialService.complete_upload(upload_id, content_hash, size_bytes) -> Material`.
- `MaterialService.get_revision(material_id, revision) -> MaterialRevision`.
- `MaterialService.mark_parsed(material_revision_id, result_ref)`.

- [x] **Step 1: Write upload and material validation tests**

  Cover allowed TXT/MD/SQL/PDF/CSV/JSON, maximum size, normalized filename, UTF-8 text validation, checksum mismatch, duplicate content, and path traversal. Assert a material with `pending/failed` parse state cannot enter a modeling input set.

- [x] **Step 2: Define material tables**

  Add:

  - `materials(id, workspace_id, name, category, source_kind, source_ref, created_by, created_at)`
  - `material_revisions(id, material_id, revision, source_sha256, size_bytes, content_uri, parse_status, parsed_uri, parse_error, created_at)`
  - unique `(material_id, revision)` and unique `(workspace_id, source_sha256, name)`.

- [x] **Step 3: Implement storage abstraction**

  Local storage uses a workspace-scoped hashed path outside the repository. A future object storage adapter must implement the same interface. Never put raw content in JSON columns or logs.

- [x] **Step 4: Implement upload lifecycle**

  The upload endpoint accepts bounded chunks or a bounded request body, calculates SHA-256, writes to a temporary object, verifies size and digest, then atomically creates a material revision. Parsing is a job, not part of the request transaction.

- [x] **Step 5: Run tests**

  ```bash
  python -m pytest backend/tests/unit/test_material_validation.py backend/tests/integration/test_material_lifecycle.py -q
  ```

- [x] **Step 6: Commit**

  ```bash
  git add backend/src/sgtrace_app/infrastructure/storage backend/src/sgtrace_app/modules/sources/materials backend/migrations backend/tests
  git commit -m "feat: add material storage lifecycle"
  ```

**Acceptance:** 用户可以上传材料并获得可追踪 revision；失败、重复、超限和未知结果都不会伪装成成功。

---

### Task 4: 实现数据源接入、结构快照和材料解析

**Files:**

- Create: `backend/src/sgtrace_app/modules/sources/connections/models.py`
- Create: `backend/src/sgtrace_app/modules/sources/connections/schemas.py`
- Create: `backend/src/sgtrace_app/modules/sources/connections/service.py`
- Create: `backend/src/sgtrace_app/modules/sources/metadata/reader.py`
- Create: `backend/src/sgtrace_app/modules/sources/metadata/snapshot.py`
- Create: `backend/src/sgtrace_app/modules/sources/lineage/parser.py`
- Create: `backend/src/sgtrace_app/modules/sources/jobs.py`
- Create: `backend/src/sgtrace_app/api/v1/sources.py`
- Create: `backend/migrations/versions/0003_sources.py`
- Modify: `backend/src/sgtrace_app/api/v1/router.py`
- Test: `backend/tests/unit/test_metadata_normalization.py`
- Test: `backend/tests/unit/test_lineage_parser.py`
- Test: `backend/tests/integration/test_sources_api.py`

**Interfaces:**

- `SourceService.create_connection(input) -> SourceConnection`.
- `SourceService.test_connection(connection_id) -> ConnectionCheck`.
- `SourceService.refresh_metadata(connection_id) -> MetadataSnapshot`.
- `SourceService.list_tables(snapshot_id, database) -> list[TableSummary]`.
- `SourceService.get_columns(snapshot_id, database, table) -> list[ColumnDefinition]`.
- `LineageParser.parse_task_sql(text) -> ParsedLineage`.
- `SourceService.build_material_selection(workspace_id) -> list[MaterialCandidate]`.

- [x] **Step 1: Write source and metadata tests**

  Use local fake connectors and fixture DDL. Assert credentials never appear in response JSON, snapshots contain table comments, column comments, datatypes, nullable and keys, and a failed refresh leaves the previous snapshot active.

- [x] **Step 2: Implement connection records**

  Add `source_connections` with encrypted/secret-reference credential fields, type, endpoint, database allowlist, last test status and revision. The API accepts a secret reference or environment-backed credential provider; it does not echo passwords.

- [x] **Step 3: Implement metadata adapters**

  The first slice implements the `ddl` adapter and the read-only `mysql+asyncmy` adapter against `information_schema`; Oracle/MaxCompute remain explicit unsupported capabilities.

- [x] **Step 4: Migrate PoC lineage logic behind a formal adapter**

  The first slice provides a bounded SQLGlot projection parser with explicit aliases and calculated expressions. Full DataWorks export and hotspot ingestion remains the next lineage task; no PoC runtime globals or fixed `yx186/cjxt/kf95598` configuration are imported.

- [x] **Step 5: Add source API**

  Implement:

  - `GET /api/v1/sources`
  - `POST /api/v1/sources`
  - `POST /api/v1/sources/{id}/test` for the environment-backed MySQL adapter
  - `POST /api/v1/sources/{id}/refresh`
  - `GET /api/v1/sources/{id}/snapshots/{revision}/tables`
  - `GET /api/v1/sources/{id}/snapshots/{revision}/tables/{table}/columns`
  - `GET /api/v1/materials`
  - upload and list endpoints; parse status is persisted as `pending`. Async parsing, preview and delete-revision endpoints remain pending.

- [x] **Step 6: Run tests and commit**

  ```bash
  python -m pytest backend/tests/unit/test_metadata_normalization.py backend/tests/unit/test_lineage_parser.py backend/tests/integration/test_sources_api.py -q
  git add backend/src/sgtrace_app/modules/sources backend/src/sgtrace_app/api/v1 backend/migrations backend/tests
  git commit -m "feat: implement source and material ingestion"
  ```

**Acceptance:** 当前第一切片可以创建 DDL/MySQL 数据源、实际测试 MySQL 连接、读取本机 MySQL `information_schema`、解析并查看结构快照、上传材料并查看 `pending` 状态；完整 DataWorks/热点血缘和异步正文解析仍是 M1 后续任务。

---

### Task 5: 实现 OntoWing 适配、材料输入集合和识别任务

**Files:**

- Create: `backend/src/sgtrace_app/integrations/ontowing/adapter.py`
- Create: `backend/src/sgtrace_app/integrations/ontowing/contracts.py`
- Create: `backend/src/sgtrace_app/integrations/poc_engine/material_input.py`
- Create: `backend/src/sgtrace_app/modules/modeling/extraction/models.py`
- Create: `backend/src/sgtrace_app/modules/modeling/extraction/schemas.py`
- Create: `backend/src/sgtrace_app/modules/modeling/extraction/service.py`
- Create: `backend/src/sgtrace_app/modules/modeling/jobs.py`
- Create: `backend/migrations/versions/0004_modeling_inputs.py`
- Test: `backend/tests/unit/test_modeling_input_set.py`
- Test: `backend/tests/unit/test_ontowing_adapter.py`
- Test: `backend/tests/integration/test_extraction_tasks.py`

**Interfaces:**

- `OntoWingAdapter.validate(kind, content, context) -> ValidationReport`.
- `OntoWingAdapter.render(kind, editor, model) -> RenderedArtifact`.
- `ModelingInputSetBuilder.build(workspace_id, material_revision_ids, snapshot_ids) -> ModelingInputSet`.
- `ExtractionService.create_task(input_set, step, instructions) -> ExtractionTask`.
- `ExtractionService.get_task(task_id) -> ExtractionTaskView`.
- `ExtractionWorker.run(task_id) -> None`.

- [ ] **Step 1: Write input-set and adapter tests**

  Assert a modeling input set contains only successful material revisions and exact snapshot revisions, is sorted deterministically, records SHA-256 and cannot mix workspaces. Assert OntoWing adapter returns diagnostics and export losses without swallowing errors.

- [ ] **Step 2: Extract OntoWing adapter**

  Move only the verified `validate_editor` / `render_member` boundary from `reference/poc/sgtrace/wing.py`. The adapter must accept explicit backend path and never mutate `sys.path` globally for the whole application. Cache the import per worker process with a health status.

- [ ] **Step 3: Define extraction records**

  Add:

  - `modeling_input_sets(id, workspace_id, revision, input_json, sha256, created_at)`
  - `extraction_tasks(id, input_set_id, step, status, instructions, progress_json, result_uri, error_code, error_detail, created_at, updated_at)`
  - `extraction_attempts(id, task_id, sequence, external_request_ref, status, response_sha256, created_at)`.

- [ ] **Step 4: Implement task phases**

  Separate `claimed`, `parsing`, `entity`, `relation`, `alignment`, `completed`, `failed`, `cancelled`. Persist progress and allow polling. Unknown external calls must stop automatic replay and require reconciliation.

- [ ] **Step 5: Implement reference-engine migration seam**

  Wrap existing metadata and editor contracts only for tests and local fallback. The formal extraction service must be able to call a real OntoWing/material recognition provider later without changing the API schema.

- [ ] **Step 6: Run tests and commit**

  ```bash
  python -m pytest backend/tests/unit/test_modeling_input_set.py backend/tests/unit/test_ontowing_adapter.py backend/tests/integration/test_extraction_tasks.py -q
  git add backend/src/sgtrace_app/integrations backend/src/sgtrace_app/modules/modeling backend/migrations backend/tests
  git commit -m "feat: add OntoWing modeling task boundary"
  ```

**Acceptance:** 用户可以组合“业务文档 + 接入 DDL / 结构快照”创建一个可轮询、可取消、可审计的识别任务；任务输入可复现，OntoWing 校验和导出错误可见。

---

### Task 6: 实现本体、R2RML 草稿、校验和采用快照

**Files:**

- Create: `backend/src/sgtrace_app/modules/modeling/drafts/models.py`
- Create: `backend/src/sgtrace_app/modules/modeling/drafts/schemas.py`
- Create: `backend/src/sgtrace_app/modules/modeling/drafts/service.py`
- Create: `backend/src/sgtrace_app/modules/modeling/snapshots/service.py`
- Create: `backend/src/sgtrace_app/modules/modeling/validation/service.py`
- Create: `backend/src/sgtrace_app/api/v1/modeling.py`
- Create: `backend/migrations/versions/0005_model_drafts.py`
- Test: `backend/tests/unit/test_snapshot_isolation.py`
- Test: `backend/tests/integration/test_modeling_api.py`

**Interfaces:**

- `DraftService.get_current(workspace_id) -> DraftView`.
- `DraftService.patch_section(draft_id, section, expected_revision, content) -> DraftView`.
- `DraftService.preview_extraction(task_id) -> CandidatePreview`.
- `DraftService.apply_candidates(draft_id, preview_id, expected_revision) -> DraftView`.
- `ValidationService.validate_draft(draft_id) -> ValidationRun`.
- `SnapshotService.adopt(draft_id, validation_run_id, expected_revision) -> ModelSnapshot`.
- `SnapshotService.get(snapshot_id) -> ModelSnapshot`.

- [ ] **Step 1: Write isolation tests**

  Assert editing a draft does not change the active snapshot; a query pinned to snapshot `N` continues to use `N` after snapshot `N+1` is adopted; applying a preview generated from an old draft revision returns `409 draft_revision_conflict`.

- [ ] **Step 2: Define model records**

  Add:

  - `model_drafts(id, workspace_id, revision, model_json, pipeline_json, rules_json, base_snapshot_id, updated_by, updated_at)`
  - `model_candidate_previews(id, draft_id, draft_revision, input_set_id, candidate_json, evidence_json, status, created_at)`
  - `model_validation_runs(id, draft_id, draft_revision, wing_report_json, r2rml_report_json, rule_report_json, status, created_at)`
  - `model_snapshots(id, workspace_id, revision, ontology_uri, mapping_uri, rules_uri, manifest_json, sha256, adopted_by, adopted_at)`.

- [ ] **Step 3: Implement section-level draft updates**

  Use optimistic concurrency with `expected_revision`. Validate JSON shape and section ownership before persisting. Do not permit the client to modify snapshot IDs, audit fields, or artifact hashes.

- [ ] **Step 4: Implement candidate preview and apply**

  Candidate preview must include material IDs, source quotes/locations, generated concepts/attributes/relations, warnings and confidence. Apply is an explicit mutation that appends or edits only allowed draft items, preserving user changes.

- [ ] **Step 5: Implement validation**

  Call OntoWing static validators, render OWL/R2RML/SWRL, run Morph-KGC on a testable configured sandbox when available, and run rule-vs-SQL cross-checks. Store all reports with status `passed`, `failed`, or `not_run`; never collapse `not_run` into pass.

- [ ] **Step 6: Implement adoption**

  Adoption requires a passed structural validation and records immutable artifact references. It updates the workspace active snapshot pointer in one transaction and emits an audit event. It does not delete previous snapshots.

- [ ] **Step 7: Add modeling API**

  Implement:

  - `GET /api/v1/modeling/draft`
  - `PATCH /api/v1/modeling/draft/{section}`
  - `POST /api/v1/modeling/previews`
  - `POST /api/v1/modeling/previews/{id}/apply`
  - `POST /api/v1/modeling/validation`
  - `GET /api/v1/modeling/validation/{id}`
  - `POST /api/v1/modeling/snapshots/adopt`
  - `GET /api/v1/modeling/snapshots`

- [ ] **Step 8: Run tests and commit**

  ```bash
  python -m pytest backend/tests/unit/test_snapshot_isolation.py backend/tests/integration/test_modeling_api.py -q
  git add backend/src/sgtrace_app/modules/modeling backend/src/sgtrace_app/api/v1 backend/migrations backend/tests
  git commit -m "feat: add model drafts validation and snapshots"
  ```

**Acceptance:** 建模用户可以从材料生成并预览候选、编辑本体和映射、执行校验、采用一个不可变快照；智能体可以明确使用哪个快照。

---

### Task 7: 迁移语义索引、血缘和规则工具为正式智能体

**Files:**

- Create: `backend/src/sgtrace_app/integrations/poc_engine/semantic_index.py`
- Create: `backend/src/sgtrace_app/integrations/poc_engine/lineage.py`
- Create: `backend/src/sgtrace_app/modules/agent/tools.py`
- Create: `backend/src/sgtrace_app/modules/agent/service.py`
- Create: `backend/src/sgtrace_app/modules/agent/schemas.py`
- Create: `backend/src/sgtrace_app/api/v1/agent.py`
- Create: `backend/migrations/versions/0006_agent_history.py`
- Test: `backend/tests/unit/test_semantic_index_snapshot.py`
- Test: `backend/tests/unit/test_agent_tools.py`
- Test: `backend/tests/integration/test_agent_api.py`

**Interfaces:**

- `SemanticIndexBuilder.build(snapshot_id) -> IndexManifest`.
- `AgentTools.trace_field(snapshot_id, name, context) -> ToolResult`.
- `AgentTools.trace_screenshot(snapshot_id, fields, ocr, context) -> ToolResult`.
- `AgentTools.explain_rule(snapshot_id, concept) -> ToolResult`.
- `AgentService.chat(workspace_id, actor_id, snapshot_id, message, ocr, fields) -> AgentAnswer`.

- [ ] **Step 1: Write semantic and safety tests**

  Cover source candidates only from OWL/R2RML, table schema restoration, rule-chain output, unknown field abstention, screenshot rows excluded from LLM prompt, and fabricated `schema.TABLE.COLUMN` in LLM prose flagged as unverified.

- [ ] **Step 2: Migrate `SemanticIndex` behind snapshot storage**

  Load only the immutable artifact manifest for the requested snapshot. Cache indexes by `(workspace_id, snapshot_id, artifact_sha256)`. An index build failure marks the snapshot query-unavailable; it does not silently rebuild from current draft.

- [ ] **Step 3: Migrate evidence and QA logic**

  Extract tested scoring, value checks, page consistency and lineage tracing from `reference/poc/sgtrace/qa.py` and `evidence.py`. Replace fixed database names and global `DATA` paths with injected snapshot metadata, source adapters and evidence repositories.

- [ ] **Step 4: Implement tool contracts**

  Tool responses must include structured `status`, `sources`, `evidence`, `lineage`, `derived_metrics`, `alternatives`, `confidence`, and `snapshot_id`. Results must distinguish `located`, `derived`, `ambiguous`, `needs_review`, and `not_found`.

- [ ] **Step 5: Implement model provider adapter**

  Create `LLMProvider` with timeout, max rounds, tool-only field facts, prompt redaction, and fallback to deterministic rules. Store provider/model/request references, not API keys or raw sample rows.

- [ ] **Step 6: Persist agent history**

  Add:

  - `agent_conversations(id, workspace_id, actor_id, title, created_at, updated_at)`
  - `agent_turns(id, conversation_id, snapshot_id, question_text, ocr_context_hash, response_json, mode, created_at)`
  - `agent_tool_calls(id, turn_id, tool_name, args_redacted_json, result_sha256, status, created_at)`.

- [ ] **Step 7: Add agent API**

  Implement:

  - `POST /api/v1/agent/conversations`
  - `GET /api/v1/agent/conversations`
  - `GET /api/v1/agent/conversations/{id}`
  - `POST /api/v1/agent/conversations/{id}/turns`
  - `GET /api/v1/agent/snapshots/{id}/readiness`

- [ ] **Step 8: Run tests and commit**

  ```bash
  python -m pytest backend/tests/unit/test_semantic_index_snapshot.py backend/tests/unit/test_agent_tools.py backend/tests/integration/test_agent_api.py -q
  git add backend/src/sgtrace_app/integrations backend/src/sgtrace_app/modules/agent backend/src/sgtrace_app/api/v1 backend/migrations backend/tests
  git commit -m "feat: add snapshot-bound trace agent"
  ```

**Acceptance:** 一个问题完整绑定到一个已采用模型快照；工具事实可复查；模型不可用、字段未找到、候选歧义和证据不足均有明确状态。

---

### Task 8: 将正式前端接入数据源模块

**Files:**

- Create: `frontend/src/shared/api/http.ts`
- Create: `frontend/src/shared/api/sources.ts`
- Create: `frontend/src/shared/types/sources.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/styles.css`
- Modify: `frontend/src/modules/sources/index.tsx`
- Create: `frontend/src/modules/sources/ConnectionList.tsx`
- Create: `frontend/src/modules/sources/MaterialList.tsx`
- Create: `frontend/src/modules/sources/SchemaBrowser.tsx`
- Create: `frontend/src/modules/sources/sources.css`
- Test: `frontend/src/modules/sources/*.test.tsx` 或 Playwright 页面测试

**Interfaces:**

- `SourcesApi.list()`, `create()`, `test()`, `refresh()`, `tables()`, `columns()`, `materials()`, `upload()`.
- UI state maps `idle/loading/succeeded/failed` separately; material state maps `pending/parsing/succeeded/failed`.

- [ ] **Step 1: Write API client tests**

  Test JSON error normalization, request cancellation, upload progress, and rejection of responses missing IDs, revisions or checksums.

- [ ] **Step 2: Replace placeholder source page**

  Keep the confirmed demo shell and color tokens. Add connection list, DDL fallback, material upload/preview, status badges, source snapshot revision and table/column browser.

- [ ] **Step 3: Add material selection handoff**

  Provide a selection model matching backend `ModelingInputSet`: material revision IDs plus structure snapshot IDs. Do not pass raw file contents to modeling page state.

- [ ] **Step 4: Verify desktop and narrow layouts**

  Use the confirmed demo behavior as a visual reference. Check keyboard focus, error messages, upload cancellation, duplicate materials and no horizontal overflow.

- [ ] **Step 5: Run build and commit**

  ```bash
  npm --prefix frontend run build
  git add frontend/src
  git commit -m "feat: connect formal source module"
  ```

**Acceptance:** 正式前端可以通过 API 管理数据源和材料，不使用 localStorage 或本地 mock 作为事实来源。

---

### Task 9: 将正式前端接入 OntoWing 建模模块

**Files:**

- Create: `frontend/src/shared/api/modeling.ts`
- Create: `frontend/src/shared/types/modeling.ts`
- Modify: `frontend/src/modules/modeling/index.tsx`
- Create: `frontend/src/modules/modeling/MaterialsStep.tsx`
- Create: `frontend/src/modules/modeling/ExtractionTaskPanel.tsx`
- Create: `frontend/src/modules/modeling/DraftEditor.tsx`
- Create: `frontend/src/modules/modeling/ValidationPanel.tsx`
- Create: `frontend/src/modules/modeling/SnapshotPanel.tsx`
- Create: `frontend/src/modules/modeling/modeling.css`
- Test: modeling API/client tests and browser flow

**Interfaces:**

- `ModelingApi.getDraft()`, `patchDraftSection()`, `createPreview()`, `applyPreview()`, `startValidation()`, `getValidation()`, `adoptSnapshot()`.
- `DraftEditor` receives `{draft, expectedRevision}` and emits section patches; it never mutates active snapshot state.

- [ ] **Step 1: Write optimistic-concurrency tests**

  Assert a stale draft revision displays a conflict and reload action; preview apply cannot overwrite newer edits; adopted snapshot changes the active pointer only after validation.

- [ ] **Step 2: Build the materials step**

  Reuse the confirmed UI concept: choose business documents, DDL and structure snapshots together; show parsing status and source provenance; show extracted candidates only after a successful task.

- [ ] **Step 3: Embed OntoWing editor with formal adapter**

  Use the existing `@wing` editor only after the backend returns a draft contract. Wire changes through `patchDraftSection`; do not let the editor call old `/api/app` or local catalog mocks.

- [ ] **Step 4: Add validation and adoption panels**

  Show OntoWing diagnostics, R2RML run status, rule cross-check status and export losses separately. Adoption requires explicit user action and updates the active snapshot label.

- [ ] **Step 5: Run end-to-end browser flow**

  The flow must be: choose DDL + document → create extraction task → see progress → preview candidates → edit → validate → adopt → verify agent snapshot label. Test reload after each long-running step.

- [ ] **Step 6: Build and commit**

  ```bash
  npm --prefix frontend run build
  git add frontend/src
  git commit -m "feat: connect formal modeling module"
  ```

**Acceptance:** 建模页完成真实材料、任务、草稿、校验和采用快照闭环；草稿状态与智能体当前快照清楚分离。

---

### Task 10: 将正式前端接入字段溯源智能体

**Files:**

- Create: `frontend/src/shared/api/agent.ts`
- Create: `frontend/src/shared/types/agent.ts`
- Modify: `frontend/src/modules/agent/index.tsx`
- Create: `frontend/src/modules/agent/Composer.tsx`
- Create: `frontend/src/modules/agent/ConversationHistory.tsx`
- Create: `frontend/src/modules/agent/TraceResult.tsx`
- Create: `frontend/src/modules/agent/EvidencePanel.tsx`
- Create: `frontend/src/modules/agent/agent.css`
- Test: agent API/client tests and browser flow

**Interfaces:**

- `AgentApi.createConversation()`, `listConversations()`, `getConversation()`, `createTurn()`, `getSnapshotReadiness()`.
- `TraceResult` renders only structured source/evidence fields; the natural-language summary cannot inject arbitrary physical columns.

- [ ] **Step 1: Write result rendering tests**

  Cover located, derived, ambiguous, needs-review and not-found results; ensure source columns are copied from structured tool results and evidence expand/collapse does not change the answer.

- [ ] **Step 2: Migrate confirmed workspace shell**

  Keep the left navigation, history search, warm-white/blue palette, new-trace behavior and responsive drawer from `product-demo`. Replace local state and mock query service with API calls.

- [ ] **Step 3: Implement composer inputs**

  Support question text, OCR text and optional context. Show active snapshot readiness and ID. Do not send sample rows or credentials to the model endpoint.

- [ ] **Step 4: Implement conversation history**

  Save turns server-side with snapshot IDs. Reloading a history entry must render the historical snapshot label and not silently re-run it against the current snapshot.

- [ ] **Step 5: Run browser acceptance flow**

  Verify:

  1. Ask “户号来自哪个字段？” and see `schema.TABLE.COLUMN`.
  2. Ask “欠费金额怎么算？” and see two source columns plus formula and filter.
  3. Ask an unknown field and see `not_found`.
  4. Ask a rule concept and see rule chain and source fields.
  5. Adopt a new model, start a new turn, and confirm the old conversation remains on the old snapshot.

- [ ] **Step 6: Build and commit**

  ```bash
  npm --prefix frontend run build
  git add frontend/src
  git commit -m "feat: connect formal trace agent module"
  ```

**Acceptance:** 正式前端完成真实智能体查询、历史快照和证据展示闭环；没有 demo localStorage 或本地词汇模拟路径。

---

### Task 11: 统一权限、审计、错误和可观测性

**Files:**

- Create: `backend/src/sgtrace_app/api/v1/auth.py`
- Create: `backend/src/sgtrace_app/infrastructure/audit/service.py`
- Create: `backend/src/sgtrace_app/infrastructure/observability/logging.py`
- Modify: `backend/src/sgtrace_app/api/v1/router.py`
- Modify: all three module services
- Test: `backend/tests/contract/test_auth_and_errors.py`
- Test: `backend/tests/integration/test_audit.py`

**Interfaces:**

- `CurrentUser` and `CurrentWorkspace` dependencies.
- `AuditService.record(event)`.
- Error envelope `{code, message, request_id, details?}`.
- `GET /api/healthz` for process, `GET /api/readyz` for database/storage/OntoWing capability status.

- [ ] **Step 1: Write access and audit tests**

  Assert a workspace member can use all three modules; a non-member receives 403; there is no role-specific endpoint matrix; mutations create an audit event without credentials or raw sample rows.

- [ ] **Step 2: Implement identity adapter**

  Start with a local development identity header/token adapter and a deployment-configured external identity adapter. Keep a single permission set named `workspace_member`; do not add `admin/modeler/analyst` product roles.

- [ ] **Step 3: Normalize errors**

  Map validation, conflict, missing snapshot, unsupported connector, parse failure, external timeout and unknown external result to stable codes. Add request IDs and structured logs with workspace/user/object IDs.

- [ ] **Step 4: Add readiness and metrics**

  Expose database, storage, OntoWing adapter and worker readiness separately. Log job duration, parse status, validation result, index build status and agent fallback reason without storing prompts or credentials.

- [ ] **Step 5: Run contract tests and commit**

  ```bash
  python -m pytest backend/tests/contract/test_auth_and_errors.py backend/tests/integration/test_audit.py -q
  git add backend/src/sgtrace_app backend/tests
  git commit -m "feat: add workspace auth audit and readiness"
  ```

**Acceptance:** 所有人共享同一模块权限，数据隔离、错误语义、审计和 readiness 可验证；日志不泄露秘密和样例数据。

---

### Task 12: 建立本地部署、备份和发布验收

**Files:**

- Create: `docker-compose.dev.yml`
- Create: `docker/backend.Dockerfile`
- Create: `docker/frontend.Dockerfile`
- Create: `deploy/README.md`
- Create: `deploy/migrations.sh`
- Create: `deploy/backup.sh`
- Modify: `.gitignore`
- Test: `backend/tests/integration/test_compose_contract.py`

**Interfaces:**

- Local compose starts MySQL, backend API and frontend dev/prod preview without customer data.
- Migration command is explicit and idempotent.
- Backup includes database schema/data metadata and material object manifest, not plaintext credentials.

- [ ] **Step 1: Write deployment contract tests**

  Validate required environment variables, health checks, no public bind by default, migration before worker, and frontend `/api` proxy. Assert the image does not copy `reference/poc/data/gold` into the production image.

- [ ] **Step 2: Create local compose**

  Provide MySQL and formal backend/frontend. Use named volumes for database and local material storage. Bind only `127.0.0.1`. Do not include the old public tunnel, demo Basic auth, or MySQL DROP/CREATE route.

- [ ] **Step 3: Add migration and backup commands**

  `deploy/migrations.sh` runs Alembic with an explicit database URL. `deploy/backup.sh` creates a timestamped DB dump and material manifest; it refuses to run when the target path is world-readable.

- [ ] **Step 4: Add release checklist**

  Document environment, migration, readiness, first-source onboarding, first-model adoption, agent smoke test, rollback to previous snapshot, backup restore, log redaction and shutdown.

- [ ] **Step 5: Run release checks and commit**

  ```bash
  docker compose -f docker-compose.dev.yml config
  python -m pytest backend/tests/integration/test_compose_contract.py -q
  make check
  git add docker docker-compose.dev.yml deploy .gitignore
  git commit -m "chore: add formal local deployment contract"
  ```

**Acceptance:** 开发环境可复现、迁移可回滚、健康和 ready 状态清晰；正式镜像不带 PoC gold、旧 demo 路由或明文密钥。

---

## Cross-Stage Acceptance Checklist

- [ ] 三个模块均能在同一工作台中操作，所有用户使用相同权限。
- [ ] 数据源接入支持只读连接、DDL、业务文档、结构快照、材料版本和失败状态。
- [ ] 建模支持多材料输入、实体/关系识别、草稿、R2RML、校验、导出、采用快照。
- [ ] 智能体只从采用快照建立 SemanticIndex，结果绑定 snapshot ID，证据可展开。
- [ ] `schema.TABLE.COLUMN` 只来自工具结构化返回；大模型未验证字段会被标记。
- [ ] 草稿更新不会污染已采用模型；历史对话不会被当前模型重算。
- [ ] OntoWing 校验、Morph-KGC 实跑、SWRL/SQL 对账、约束检查均有独立状态。
- [ ] 数据库、材料、任务、快照、对话、审计记录可迁移、备份和恢复。
- [ ] 正式 API 没有 demo 登录、角色、建库、旧 `/demo` 和 localStorage 事实源。
- [ ] `make check`、部署契约、浏览器验收和回滚演练全部有记录。

## Recommended First Sprint

第一轮只完成 M0 + M1 的最小垂直闭环：

1. 完成 Task 1–3，建立正式数据库、材料存储和任务基础。
2. 完成 Task 4 的 DDL/结构快照读取，不接真实 Oracle/MaxCompute。
3. 正式前端先完成数据源列表、材料上传和结构浏览。
4. 用一份合成 DDL + 一份业务说明创建材料集合，成功创建解析任务并查看结果。
5. 以这一闭环作为后续 OntoWing 识别集成的输入契约。

第一轮不做登录页面、LLM 联调、生产容器和第二业务域；这些要等材料和任务身份稳定后再接入。
