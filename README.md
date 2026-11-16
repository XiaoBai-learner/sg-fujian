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

正式前端目前提供三个模块的工程入口和服务连通检查，正式后端提供应用装配和健康接口。它们是开发骨架，业务操作尚未实现；完整交互以 `product-demo/` 为验收参照。正式入口不使用 demo 的 localStorage 模拟服务，也不自动加载合成数据或运行 PoC 流水线。

## 开发环境

使用 Python 3.12+、Node.js 22.18+。在仓库根目录安装：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
npm --prefix frontend ci
npm --prefix product-demo ci
```

产品原型引用相邻 `../ontowing/frontend/src` 的编辑器，`ONTOWING_FRONTEND` 可覆盖该位置。参考引擎引用相邻 `../ontowing/backend` 的纯领域模块，`ONTOWING_BACKEND` 可覆盖。正式服务骨架不要求 OntoWing、MySQL 或模型服务已经运行。

## 常用命令

```bash
make api                 # 正式后端：127.0.0.1:8765
make web                 # 正式前端：127.0.0.1:5173；/api 代理到 8765
make demo                # 已确认原型：127.0.0.1:4180
make test                # 正式后端与参考引擎全部测试，包含 R2RML 实跑
make check-web           # 正式前端类型检查与构建
make check-demo          # 已确认原型测试与构建，包含架构文档打包
make check               # 上述全部检查
```

这些命令按需执行，项目整理不会自动启动服务。`/api/healthz` 仅检查进程存活，不代表数据库、本体或模型服务已就绪。尚未实现的业务接口返回 404，不返回模拟成功。

## 开发顺序

1. **数据源接入**：连接与材料持久化、DDL / 结构快照、正文解析和来源身份，接通正式前端。
2. **OntoWing 建模**：多材料识别任务、草稿保存、对象关系与 R2RML 编辑、校验与采用快照。
3. **溯源智能体**：从采用快照建立语义索引，迁移字段 / 截图 / 规则工具，保存对话、来源与证据。

每一步都应形成真实可操作的前后端闭环，再继续下一步。先从 `reference/poc/` 提取经过测试的独立能力，避免直接复制其固定库名、全局状态和演示数据生命周期。

## 清理后的保留规则

产品文档仅维护 `docs/product.md` 与 `docs/architecture.html`。旧 PRD、角色审批方案、过程计划、旧前端与旧部署入口已移出活动项目；清理前的改动与文件在仓库外保留了恢复备份，位置见已忽略的 `artifacts/cleanup-backup-path.txt`。

`.env`、口令、真实客户数据和运行产物不进入 Git。测试数据只位于 `reference/poc/data/`；生成器只允许重建这一目录。
