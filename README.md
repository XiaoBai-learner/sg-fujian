# 字段溯源工作台

`dev/1.0.0` 的开发基线是用户确认的三模块工作台：**数据源接入 → OntoWing 本体建模 → 基于本体与 R2RML 的字段溯源智能体**。所有人使用相同功能。

- 当前确认的交付交互：`frontend/`；`product-demo/` 仅保留作历史交互参照。
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
product-demo/                     历史交互原型，不作为正式运行与验收入口
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

正式前端已接通真实 DDL / SQL 建模闭环：上传材料 → 结构与 SQL 证据分析 → 本体草稿 → OntoWing 静态校验与导出 → 采用快照 → 字段溯源。材料、任务、草稿和快照由正式后端持久化；按分组管理多个独立本体模型，刷新按模型恢复草稿和采用版本。`product-demo/` 继续保留为独立交互参照，不参与正式计算。

在 `/sources` 配置并测试 MySQL 连接，选择一个或多个数据库，将真实 DDL 采集到材料库；也可在 `/materials` 右上角“新建文档”弹窗中上传或粘贴 UTF-8 SQL / TXT / Markdown。进入 `/modeling` 新建具名模型后，只选用这些已接入材料；至少提供一份含 `schema.TABLE` 或 `USE` 的 MySQL DDL，可组合 SELECT、CTE、CREATE VIEW 和 INSERT…SELECT 任务。系统按 AST 提取实际列、别名、计算表达式、完整查询口径、外键与 JOIN；不执行上传 SQL。完整本体图可点击类、属性和关系编辑，改动保存到服务端并使旧检查失效。缺主键、未知列、冲突任务或解析失败会明确报告。

“模型语义增强”默认关闭；开启后选定材料发送到 `.env` 配置的模型服务。模型只能对已有候选的有依据名称给出建议，不创造物理字段；新叫法和业务推断需人工核对。结构路径与增强路径都不能证明业务概念世界完整。PDF、动态 SQL、其他方言、增量调度、图中新增 / 删除对象及效果评测尚未完成。

字段来源从已采用 OWL / R2RML 解析，计算字段通过依赖清单核对导出的实际列；多种计算口径保持歧义。校验页可下载采用版本的 OWL / R2RML。当前执行了 OntoWing 静态检查，**未执行本轮 Morph-KGC 实跑或业务口径 SQL 对账**；不能将“校验通过”当作准确率。正式应用没有内置示例材料、模拟查询或固定推荐问题；测试夹具仅位于测试目录，不进入构建包。

打开工作台后必须登录。空数据库首次打开时由用户创建首个账户，不提供默认账号口令；登录后从右上角账户菜单进入账户管理，可新增账户、修改名称、启停其他账户及修改自己的密码。所有成员共享同一工作区和相同功能，包括账户管理，不设置角色。密码使用 Argon2id 散列；会话存于数据库，浏览器使用 HttpOnly / SameSite=Strict Cookie，写接口校验会话绑定的 CSRF 令牌。退出、改密和停用会使相应会话失效；修改密码会注销所有设备。

真实操作试用材料见 [营销域试用包](trials/marketing_v1/README.md)：16 张源表 DDL、任务血缘及 22 条热点 SQL，配套本地隔离 MySQL 合成数据、100 道独立存放的问题和标准答案。上传时只选择试用包 `inputs/` 中的四份文件；建模采用后可运行只读批量评测。试用包 SQL 等价核对与正式建模映射物化是不同检查。

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

正式服务 `make api` 从项目根目录 `.env` 读取配置（不覆盖已注入的环境变量）：`DATABASE_URL`、`STORAGE_ROOT`、`MYSQL_*`，可选 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`。当前本机使用独立产品库 `sgtrace_product_local` 与 `var/product-local/storage`，保留用户自行创建的账户、连接、材料和模型，不自动初始化业务数据；旧 `sgtrace_product` 保留此前测试记录，与源库分开。新环境先执行 `DATABASE_URL=... .venv/bin/python -m alembic -c backend/alembic.ini upgrade head`，迁移到 `0007_model_context`；不用把密码写入 Git。HTTPS 部署须设置 `SGTRACE_COOKIE_SECURE=1`，首次账户初始化仅在受控部署入口进行；当前只在本机开放。

这些命令按需执行，不会自动对外开放。`/api/healthz` 仅检查进程存活，不代表数据库、本体或模型服务已就绪。尚未实现的业务接口返回 404，不返回模拟成功。

## 当前确认基线（2026-11-18）

当前正式工作台已由用户确认，可以作为下一轮研发基线。仅有一层左侧功能导航，顶部保留品牌与账户，不显示固定领域标签或重复导航；模型目录采用行内分组筛选。

| 模块 | 本轮已接通能力 |
|---|---|
| 数据源接入 | MySQL 连接新建 / 编辑 / 测试、实际数据库发现、单选 / 多选 / 全选、只读 DDL 采集；文档统一在右上角弹窗上传 / 粘贴，按行展示介绍与正文 |
| 本体建模 | 多个独立具名模型及分组；选用既有材料；手写业务流程按模型保存，生成时保留原文；类属性卡片、大画布、关系编辑、证据、服务端草稿、校验与采用 |
| 字段溯源 | 显式选择已采用模型；字段 / 同义名称匹配、物理来源、规则证据评分；截图附件鉴权上传与预览 |

连接密码加密保存，密钥为 `STORAGE_ROOT/.connection-key`。备份与恢复必须同时保留数据库、材料存储与该密钥，不得将它们提交 Git。迁移 `0006_workbench` 将已有生成记录归入独立模型，`0007_model_context` 增加模型业务流程说明，不清空已有记录。

2026-11-18 本地提交前验证：开启本地 MySQL 集成的后端 / 参考引擎全量回归 98 项通过；正式前端 31 项、历史原型 7 项测试通过，两套类型检查与构建通过。这些是功能回归证据，不是字段溯源准确率或客户验收结论；远端 CI 需在推送后另行确认。

## 下一轮研发重点

1. **建模方法**：完善业务流程、文档与 DDL / SQL 多证据对齐、业务概念归纳和待确认项处理；现有语义增强仅限已有候选与定位原文，不能称为已支持自由描述自动建模。
2. **问答能力**：接通自然语言需求理解和受控工具调用、歧义澄清与永久对话历史。截图当前只保存附件，自动读图未接入；是否引入外部表头识别需保持不做 OCR、不发送样例行的业务边界。
3. **效果与交付**：接入正式版本的映射物化及独立 SQL 对账，执行试用包 100 题与独立留出集评测，再依据评测结果做置信度校准；完善任务恢复、PDF / 多方言与部署验收。

上述为待办优先级，不表示已完成或在本次提交中执行。下一轮沿用当前用户确认的页面结构，按真实前后端闭环逐项开发。

## 清理后的保留规则

产品文档仅维护 `docs/product.md` 与 `docs/architecture.html`。旧 PRD、角色审批方案、过程计划、旧前端与旧部署入口已移出活动项目；清理前的改动与文件在仓库外保留了恢复备份，位置见已忽略的 `artifacts/cleanup-backup-path.txt`。

`.env`、口令、真实客户数据和运行产物不进入 Git。测试数据只位于 `reference/poc/data/`；生成器只允许重建这一目录。
