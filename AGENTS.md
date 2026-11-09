# AGENTS.md

福建电力"业务字段溯源"PoC。

## 一期范围

输入：业务人员的一封取数邮件，内容是截图 OCR 文本加上要问的中文字段名。
输出：每个字段对应的源系统原表和原表字段（`schema.TABLE.COLUMN`），附带置信度、证据链和血缘路径。

- 不做 OCR，客户自己有 OCR 能力。输入直接就是 OCR 文本。
- 不做码值翻译，比如 `01` 对应"柜台"。
- 不做数据治理和合并。同义字段只作为可接受的等价答案。
- 只做一个业务领域：营销域，福州试点。电力系统按领域分别建本体再组合，不做全域本体。

## 架构

```
MySQL information_schema ─┐
（或 DDL 文件回退）        ├─ sgtrace.builder ─→ wing-model-editor/1 + wing-pipeline-editor/2
DataWorks 血缘导出 + 任务 SQL ┤                       │
热点 SQL 日志 ─────────────┘                       ▼ OntoWing 领域库（validate_editor / render_member）
                                         ontology.ttl（OWL） + mapping.ttl（R2RML）
                                                   │            │
                                     Morph-KGC 在沙箱实跑校验     ▼
                                                   sgtrace.semantic（只读导出文件建索引）
                                                                │
                              截图 OCR + 字段 ─→ sgtrace.qa ─→ 原表.原字段 + 证据
```

- **OntoWing 依赖方式**：以源码目录引用 `../ontowing/backend`（可用 `ONTOWING_BACKEND` 覆盖），只导入 `app.domain.modeling_profiles` 与 `app.domain.modeling_artifacts.projection`。这两个是纯领域模块，不依赖 Django、数据库或网络。不走 OntoWing HTTP 服务：它要求 Manager 签发的 JWT、角色绑定文件和 MySQL 业务库，本地无法独立运行。验证基线为 OntoWing `afd9bb12`。
- **OntoWing 导出损失**（`render_member` 返回的 losses，属于预期）：
  - `binding_schema_name`：R2RML 的 `rr:tableName` 不带库名，`sgtrace.semantic` 用 pipeline 里的 `schema_name` 补回。
  - `attribute_sensitivity`、`concept_top_category`、`relation_characteristics`：这三类信息不进入 TTL。
  - IRI 命名空间固定为 `https://vocab.alita.dev/gongshang/`，这是 OntoWing 内置的，不是我们选的。
- **OntoWing 校验规则**（构建时必须满足）：
  - 实体键不能为可空列。
  - 关联的 joins 必须完整覆盖父绑定的 key_columns。
  - 属性只能映射到其 concept 自身或祖先上的绑定。
  - 同一 (表, 列) 只能对应一种 datatype。
- **问答只走本体 + R2RML**：源字段候选全部来自 `SemanticIndex`（解析导出的 TTL），不直接查 DDL。中台列名注释只用于判定页面背后的中台表，再沿血缘追到源字段。

## 目录

```
sgtrace/                溯源服务
  config.py             路径、MySQL（.env）、OntoWing 位置
  metadata.py           读 MySQL information_schema / 解析 DDL；在 MySQL 建库
  evidence.py           血缘（导出 + 任务 SQL 解析 + 命名约定）、JOIN 证据、热度
  glossary.py           人工领域词表：缩写、同义词组、CIM 对应（待专家确认）
  builder.py            生成 OntoWing model/pipeline 编辑器 JSON 与表字典快照
  wing.py               OntoWing 适配层
  verify.py             Morph-KGC 在沙箱 SQLite 上执行 R2RML
  semantic.py           从 ontology.ttl + mapping.ttl 建“叫法→属性→物理列”索引
  qa.py                 截图溯源与自由提问
  evaluate.py           对 gold 评测：开发集、留出集、关键词基线、消融
  pipeline.py           串起全流程并写 artifacts/
  server.py             FastAPI 演示服务（127.0.0.1:8765，无鉴权，仅本机）
web/                    演示前端（无构建步骤）：构建本体与映射 / 本体浏览 / 字段溯源问答
artifacts/              构建产物（gitignore）：ontology.ttl、mapping.r2rml.ttl、wing_*.json、build_report.json
datagen/                测试数据生成器（确定性）
  sources.py / gen.py / dataplatform.py / pages.py / hotsql.py / lineage.py / ontology.py
  mysql_ddl.py          生成本地 MySQL 替身库 DDL（只有表结构，不建外键）
  build.py              入口
data/
  inputs/               客户能提供的东西，流水线只能读这里
    ddl/source/<系统>/schema.sql   源系统原方言 DDL
    ddl/platform/schema.sql        中台 DDL（MaxCompute）
    ddl/mysql/<库>.sql             本地 MySQL 替身库 DDL（4 个库）
    samples/ hot_sql/ dataworks/   样例数据、热点 SQL、血缘导出与任务 SQL
    requests/                      开发集：20 个需求 / 90 个字段
    requests_holdout/              留出集：7 个需求 / 38 个字段（新页面、新叫法，调优时不看）
  gold/                 标准答案，流水线禁止读取，只用于评测
  sandbox/              带数据的 SQLite（gitignore）：值校验、R2RML 实跑
tests/                  test_dataset.py（数据集）+ test_sgtrace.py（服务）
docs/review_checklist.md  mock 数据人工审阅清单
```

## 命令

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
python3 datagen/build.py                   # 重新生成 data/（会先删除整个 data/）
.venv/bin/python -m pytest -q              # 全部测试（含约 30 秒的 R2RML 实跑）
.venv/bin/python -m pytest -q -m "not slow"
.venv/bin/python -m sgtrace.server         # 打开 http://127.0.0.1:8765
```

MySQL：本机是 `/usr/local/mysql`（9.3.0，不在 PATH 中）。凭据放在项目根目录 `.env`（已 gitignore），包含 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`。演示页上点“在 MySQL 中建库建表”会创建 `yx186`、`cjxt`、`kf95598`、`sgfj_dataplatform` 四个库，执行 DROP + CREATE，只建表结构。未配置时自动退回读 DDL 文件，两条路径产出同一份元数据结构。

## 当前结果（DDL 来源，2026-11-09）

- 本体：16 个概念、91 个属性、22 条关系。数据管道映射：19 个绑定。OntoWing 静态校验通过（sources=pass）。
- R2RML 实跑：68 万个三元组，没有空概念。唯一 1 个悬空引用是根单位 `351` 不在组织表中，这是数据如此，不是映射错误。
- 严格准确率：

  | 数据集 | 本系统 | 关键词基线 |
  |---|---|---|
  | 开发集 | 100% | 38.9% |
  | 留出集 | 94.7% | 26.3% |

- 留出集的 2 个错例：
  - “负荷率”与“负载率”同义，但词表里没有。
  - “缴费渠道”与“缴费方式”同义，但词表里没有。
- 消融（开发集，严格准确率）：

  | 去掉的部分 | 严格准确率 |
  |---|---|
  | 同义词 | 94.4% |
  | 值校验 | 98.9% |
  | 中台血缘 | 85.6% |
  | 任务 SQL 解析（只用 DataWorks 导出） | 66.7% |

  任务 SQL 解析的贡献最大。客户现场能否拿到任务代码，是关键前提。
- 开发集 100% 是在调优规则时看过的，不能作为效果结论。对外说明效果用留出集和真实客户数据。

## 约定

- 修改 datagen 或 sgtrace 后必须跑 `pytest`。
- 规则调优只看开发集。调完再跑留出集，不要针对留出集错例改规则。如果改了，就要再补一套新的留出集。
- `glossary.py` 是人工领域知识，消融里单独报告它的贡献。CIM 对应标注为“待专家确认”。
- 新增业务领域时，单独建一套 `sources_<领域>.py`、词表和本体，不要并入营销域。
- 不要提交 `.env`、真实客户数据或产物。所有姓名、电话、编号都是生成的。
- 演示服务没有鉴权，只能监听 127.0.0.1。
