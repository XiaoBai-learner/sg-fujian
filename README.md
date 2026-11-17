# 字段溯源工作台

`dev/1.0.0` 的开发基线是用户确认的三模块工作台：**数据源接入 → OntoWing 本体建模 → 基于本体与 R2RML 的字段溯源智能体**。所有人使用相同功能。

- 已确认交互原型：[product-demo/](product-demo/README.md)。
- 已确认产品架构：[docs/architecture.html](docs/architecture.html)。
- 产品功能与方法：[docs/product.md](docs/product.md)。

## 项目目录

```text
frontend/                         正式前端，React + TypeScript + Vite
  src/
    app/                          工作台外壳、导航、全局样式
    modules/
      sources/                    数据源、材料、元数据与血缘
      modeling/                   文档 / DDL 识别、本体与 R2RML
      agent/                      字段溯源对话、结果与依据
    shared/api/                   正式 HTTP 客户端
backend/
  pyproject.toml                  正式 Python 包与运行依赖
  src/sgtrace_app/
    main.py                       FastAPI 装配
    modules/
      sources/                    数据源与统一材料业务边界
      modeling/                   本体、映射与采用快照业务边界
      agent/                      受控查询与问答业务边界
    integrations/                 OntoWing、模型服务、引擎适配
    infrastructure/               持久化、文件存储与任务执行
  tests/                          正式服务测试
product-demo/                     已确认 demo，保留作产品验收参照
docs/
  architecture.html               已确认的产品功能架构图
  product.md                      对应功能、特色方法与实现边界
reference/poc/                    可复用引擎与回归依据，非正式运行入口
  sgtrace/                        元数据、SQL 血缘、本体、映射、推理、溯源
  datagen/                        确定性测试数据生成器
  data/                           合成输入、评测答案与生成的沙箱
  tests/                          引擎与数据回归
Makefile                          统一开发与检查命令
pytest.ini                        正式服务 + 参考引擎的测试发现
```

正式前端已接通真实 DDL / SQL 建模闭环：上传材料 → 结构与 SQL 证据分析 → 本体草稿 → OntoWing 静态校验与导出 → 采用快照 → 字段溯源。材料、任务、草稿和快照由正式后端持久化；刷新可恢复最新成功任务和采用模型。`product-demo/` 继续保留为独立交互参照，不参与正式计算。

在 `/modeling` 上传 UTF-8 SQL / TXT / Markdown，至少提供一份含 `schema.TABLE` 或 `USE` 的 MySQL DDL；可组合 SELECT、CTE、CREATE VIEW 和 INSERT…SELECT 任务。系统按 AST 提取实际列、别名、计算表达式、完整查询口径、外键与 JOIN；不执行上传 SQL。完整本体图可点击类、属性和关系编辑，改动保存到服务端并使旧检查失效。缺主键、未知列、冲突任务或解析失败会明确报告。

“模型语义增强”默认关闭；开启后选定材料发送到 `.env` 配置的模型服务。模型只能对已有候选的有依据名称给出建议，不创造物理字段；新叫法和业务推断需人工核对。结构路径与增强路径都不能证明业务概念世界完整。PDF、动态 SQL、其他方言、增量调度、图中新增 / 删除对象及效果评测尚未完成。

字段来源从已采用 OWL / R2RML 解析，计算字段通过依赖清单核对导出的实际列；多种计算口径保持歧义。校验页可下载采用版本的 OWL / R2RML。当前执行了 OntoWing 静态检查，**未执行本轮 Morph-KGC 实跑或业务口径 SQL 对账**；不能将“校验通过”当作准确率。合成示例仍可显式载入，和真实服务模式隔离。

## 开发环境

使用 Python 3.12+、Node.js 22.18+。在仓库根目录安装：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
npm --prefix frontend ci
npm --prefix product-demo ci
```

产品原型引用相邻 `../ontowing/frontend/src` 的编辑器，`ONTOWING_FRONTEND` 可覆盖该位置。参考引擎引用相邻 `../ontowing/backend` 的纯领域模块，`ONTOWING_BACKEND` 可覆盖。真实校验需要该 OntoWing 领域库；LLM 仅在启用语义增强时调用。OntoWing 在子进程内导入，不修改 HTTP 进程的全局导入路径。

## 常用命令

```bash
make api                 # 正式后端：127.0.0.1:8765
make web                 # 正式前端：127.0.0.1:5173；/api 代理到 8765
make demo                # 已确认原型：127.0.0.1:4180
make test                # 正式后端与参考引擎全部测试，包含 R2RML 实跑
make check-web           # 正式前端行为检查、类型检查与构建
make check-demo          # 已确认原型测试与构建，包含架构文档打包
make check               # 上述全部检查
```

正式服务 `make api` 从项目根目录 `.env` 读取配置（不覆盖已注入的环境变量）：`DATABASE_URL`、`STORAGE_ROOT`、`MYSQL_*`，可选 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`。本机产品库为 `sgtrace_product`，与只读源库分开。新环境先执行 `DATABASE_URL=... .venv/bin/python -m alembic -c backend/alembic.ini upgrade head`；不用把密码写入 Git。

这些命令按需执行，不会自动对外开放。`/api/healthz` 仅检查进程存活，不代表数据库、本体或模型服务已就绪。尚未实现的业务接口返回 404，不返回模拟成功。

## 开发顺序

1. **数据源接入**：连接与材料持久化、DDL / 结构快照、正文解析和来源身份，接通正式前端。
2. **OntoWing 建模**：多材料识别任务、草稿保存、对象关系与 R2RML 编辑、校验与采用快照。
3. **溯源智能体**：从采用快照建立语义索引，迁移字段 / 截图 / 规则工具，保存对话、来源与证据。

每一步都应形成真实可操作的前后端闭环，再继续下一步。先从 `reference/poc/` 提取经过测试的独立能力，避免直接复制其固定库名、全局状态和演示数据生命周期。

## 清理后的保留规则

产品文档仅维护 `docs/product.md` 与 `docs/architecture.html`。旧 PRD、角色审批方案、过程计划、旧前端与旧部署入口已移出活动项目；清理前的改动与文件在仓库外保留了恢复备份，位置见已忽略的 `artifacts/cleanup-backup-path.txt`。

`.env`、口令、真实客户数据和运行产物不进入 Git。测试数据只位于 `reference/poc/data/`；生成器只允许重建这一目录。
