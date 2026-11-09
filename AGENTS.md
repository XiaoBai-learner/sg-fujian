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
                                         ontology.ttl（OWL） + mapping.ttl（R2RML） + rules.ttl（SWRL）
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

## 本体结构（对象 · 关系 · 规则）

- **层次**：6 个上位类（参与方、计量与采集设备、计量位置、计量数据、电费账务、客户服务事件），下挂 15 个业务对象；7 个规则派生类（欠费客户、投诉工单等）是业务对象的子类。层次关系写在 `glossary.py` 的 `TOP_CLASSES` 和 `CONCEPT_PARENT` 里，属于待专家确认的领域知识。
- **关系**：外键推断出 20 条一对多关系，命名优先用领域动词（`RELATION_VERBS`，如“归属供电单位”“冲抵应收”），每条都配有反向关系。另有 2 条按标识对齐的同一性关系（*_sameAs）。
- **关联表**：只有“主键 + 两个外键 + 日期”的表不建成概念，而是转成多对多关系。当前只有 C_METER_MP_RELA，转成“计量点 安装电能表”。
- **规则**（`sgtrace/rules.py`）：共 7 条，6 条事实规则 + 1 条建议规则，另有 6 条约束。
  - 规则通过属性或关系把对象连起来，并且可以引用其他规则的结论，例如“重点关注客户 = 欠费客户 ∧ 投诉客户”。
  - 规则用“源表.列”书写，构建时再解析成本体里的属性或关系。码值取自 DDL 注释，阈值是领域假设，标注了待业务确认。
- **执行与核对**：
  - `sgtrace/reason.py` 在 R2RML 物化出的实例图上，前向链执行 OntoWing 导出的 SWRL。
  - 每条规则都有一条独立 SQL（`cross_check`），在原库上重算结果，两边数量必须一致。
  - 约束检查在实例上完成，因为 OntoWing 不导出约束（导出损失记为 `rule_constraints`）。
  - 建议规则（DR）OntoWing 不导出为事实规则，只用于展示，并给出 SQL 计数供参考。

## 目录

```
sgtrace/                溯源服务
  config.py             路径、MySQL（.env）、OntoWing 位置
  metadata.py           读 MySQL information_schema / 解析 DDL；在 MySQL 建库
  evidence.py           血缘（导出 + 任务 SQL 解析 + 命名约定）、JOIN 证据、热度
  glossary.py           人工领域词表：缩写、同义词组、上位类与层次、关系动词、CIM 对应（待专家确认）
  rules.py              业务规则、派生类、约束，以及每条规则的独立 SQL 核对口径
  reason.py             在实例图上执行 SWRL 规则、检查约束
  builder.py            生成 OntoWing model/pipeline 编辑器 JSON 与表字典快照
  wing.py               OntoWing 适配层
  verify.py             Morph-KGC 在沙箱 SQLite 上执行 R2RML
  semantic.py           从 ontology.ttl + mapping.ttl 建“叫法→属性→物理列”索引
  qa.py                 截图溯源与自由提问
  evaluate.py           对 gold 评测：开发集、留出集、关键词基线、消融
  pipeline.py           串起全流程并写 artifacts/
  server.py             FastAPI 演示服务：本机模式（127.0.0.1:8765，无鉴权）/ 公网模式（SGTRACE_PUBLIC=1）
scripts/public.sh       公网演示：启动公网模式服务 + cloudflared 临时隧道（start|stop|status）
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

## 公网演示

```bash
scripts/public.sh start    # 打印 https://*.trycloudflare.com 地址；用户名 demo，口令在 .public_token
scripts/public.sh status
scripts/public.sh stop
```

- 服务仍只监听 127.0.0.1:8766，对外完全依赖 cloudflared 出站隧道。不开放端口，也不改路由器或防火墙。
- 公网模式和本机模式的区别：
  - 所有路径都要 Basic 认证，口令比较用常量时间。
  - 认证失败按 CF-Connecting-IP 限流，10 分钟内最多 20 次。
  - 禁用 MySQL 建库接口和 /api/docs。
  - 构建串行执行，60 秒一次。
  - 状态和错误信息里不返回本机路径、MySQL 账号和异常细节。
  - 加 CSP、X-Frame-Options 等安全头。
- 临时隧道（trycloudflare）没有 SLA，每次启动地址都会变，电脑休眠或断网后就失效。如果要长期使用，需要 Cloudflare 账号和自有域名，建命名隧道，再加 Cloudflare Access。
- 口令存放在 `.public_token`，权限 600，已 gitignore。轮换口令：先删除这个文件，再执行 `scripts/public.sh stop && scripts/public.sh start`。
- 演示数据全部是生成的，但服务连着本机 MySQL 的 root 账号，只读 information_schema。不要在公网模式下放开建库接口。

## 当前结果（2026-11-09）

- 本机 MySQL 已建 4 个库共 60 张表，只有表结构。从 `information_schema` 读到的结构与 DDL 文件逐表一致，MySQL 和 DDL 两条来源生成的本体也完全相同。

- 本体规模：6 个上位类、15 个业务对象、7 个派生类、89 个属性、43 条关系（含反向关系和同一性关系）、7 条规则、6 条约束；数据管道映射 19 个绑定。
- OntoWing 校验：本体、数据管道映射、规则三类全部通过。
- R2RML 实跑：68 万个三元组，按标识对齐合并了 1240 个 IRI。唯一 1 个悬空引用是根单位 `351` 不在组织表里，这是数据本身的情况。
- 规则推理：6 条事实规则的推理结果与独立 SQL 全部一致（欠费客户 47、投诉客户 113、重点关注客户 14 等），6 条约束没有违反；推理耗时约 7 秒。
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
- 两种模式都只监听 127.0.0.1。本机模式没有鉴权；对外只能走 `scripts/public.sh`（公网模式 + 隧道），不能直接监听 0.0.0.0。
