# 字段溯源：三层轻量前端

仅保留三个入口，所有人使用同一套功能：

1. **数据源接入**：管理连接配置、浏览表结构、登记 DDL、血缘与任务 SQL 材料。
2. **OntoWing 本体建模**：直接复用对象属性、关系图、R2RML 管道和规则编辑器；修改自动保存，基础检查后直接用于字段溯源。
3. **字段溯源智能体**：输入问题或 OCR 文本，查看源表原字段、计算口径和可展开依据。

没有角色切换、需求工单、复核队列和审核发布工作台。

## 运行

```bash
cd product-demo
npm install
npm run start
```

打开 <http://127.0.0.1:4180/agent>。另外两页为 `/sources` 和 `/modeling`。旧 `/workbench`、`/knowledge/*` 等链接自动进入对应的新模块。

依赖旁边的 `../../ontowing/frontend/src` 源码，与现有项目的引用方式相同。Vite 可用 `ONTOWING_FRONTEND` 配置源码目录。

```bash
npm test         # Node >= 22.18，检查模型快照隔离和未知字段拒答
npm run build    # TypeScript + Vite
npm run preview  # 构建后预览；与 start 使用同一端口，二者只运行一个
```

页面必须通过本地 HTTP 服务打开，不能双击 `index.html`。

## 原型边界

页面操作和编辑可用，连接配置、模型与对话在浏览器本地保存。它尚未执行真实数据库连接、材料解析、OntoWing 后端校验、TTL 导出或大模型推理，不保存数据库账号与口令。

`src/services/workspace.ts` 中的查询仅通过当前应用的本体属性与管道映射模拟检索。后续应替换为 `sgtrace.semantic.SemanticIndex` 对 OWL/R2RML 导出文件的真实检索。不能把这段浏览器模拟当作生产溯源引擎。

`src/services/wingCatalog.ts` 为 OntoWing 编辑器提供本地模拟目录，仅拦截同源的两个指定目录 GET 路径。后续由实际数据源目录接口替换。

`检查模型` 是本地基础检查；`用于字段溯源` 固定当前本体、映射、规则快照。编辑尚未应用时不会改变当前智能体；重新提问时采用最新应用快照。

## 设计与架构

本版以 `../docs/superpowers/specs/2026-11-16-lightweight-product.md` 为准，替代 2026-11-12 的职责与审核工作台设计。

架构图：`../docs/architecture/sgtrace-v1-architecture.html`，对应同名 JSON 为源规格。
