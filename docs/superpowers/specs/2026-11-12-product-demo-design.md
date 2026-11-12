# 1.0 产品原型设计：独立业务前端与架构图

日期：2026-11-12  
状态：已确认，进入原型实现  
分支：`dev/1.0.0`

## 目标

创建一个独立的 `product-demo/` React + Vite 前端，模拟正式产品的业务操作流程。它不连接当前演示接口，使用本地 mock service；mock service 的类型和调用方式按照未来后端契约设计。

原型需要证明以下完整闭环：

1. 业务人员提交字段溯源需求。
2. 系统产生一次可追踪的执行记录。
3. 用户查看字段来源清单、证据、计算口径和待确认项。
4. 用户提交字段反馈或复核请求。
5. 建模人员处理材料、语义模型、验证和知识草稿。
6. 审核人员比较候选版本、退回或发布。
7. 业务人员看到版本更新提示，历史结果仍固定原版本。

同时生成独立架构图：

`docs/architecture/sgtrace-v1-architecture.html`

架构图表达正式版目标架构：业务端、知识工作台、API、任务 worker、应用数据库、材料/知识包存储、数据源、OntoWing、语义索引、版本发布和查询链路。

## 不做

- 不改动现有 `frontend/`、`sgtrace/` 和当前测试。
- 不接当前 `/api/app/*` 演示接口。
- 不实现真实登录、数据库连接、OntoWing 写入、文件解析或模型调用。
- 不用静态截图代替交互；核心流程必须可以点击、切换状态和查看详情。
- 不把 mock 数据定义成未来生产数据格式之外的临时结构。

## 产品入口与角色

原型使用开发环境角色切换器，默认是业务人员；切换角色用于演示权限和工作流，不代表生产认证设计。

### 业务工作台

- `/workbench`：我的需求、待处理事项、最近结果、当前知识版本。
- `/requests/new`：新建需求，填写标题、需求说明、页面上下文、OCR 文本和字段。
- `/requests/:id`：需求详情，显示执行状态、字段来源清单、证据侧栏、澄清和导出。
- `/requests/:id/review`：提交复核、查看复核状态和处理意见。

### 知识工作台

- `/knowledge`：知识状态总览、材料变化、待处理冲突、待审核版本。
- `/knowledge/materials`：材料列表、解析状态、覆盖范围和缺口。
- `/knowledge/model`：概念、属性、关系、映射和规则的分区编辑预览。
- `/knowledge/validation`：结构验证、来源验证、业务验证和回归试问。
- `/knowledge/versions`：草稿、候选版本、版本差异、审核和发布。

### 系统管理

- `/admin/connections`：连接和元数据快照的产品化预览。
- `/admin/audit`：审计事件预览。

原型不要求每个页面都拥有独立复杂编辑器。知识模型页面以清晰的列表、详情面板和版本状态证明工作流即可；现有 OntoWing 编辑器在后续真实实现中嵌入。

## 核心业务路径

默认演示数据提供一条已完成需求：

- “欠费客户清单字段溯源”
- 8 个字段已定位
- 2 个字段需澄清
- 1 个字段未覆盖
- 当前结果固定在 `营销域 K-000012`

可操作路径：

1. 从工作台进入需求详情。
2. 查看“户号”的页面实际来源和证据路径。
3. 查看“欠费金额”的计算口径：应收金额 - 实收金额，并展开过滤条件。
4. 对“缴费渠道”提交“不正确”反馈。
5. 切换到建模人员，进入复核队列。
6. 打开知识草稿，查看该反馈关联的属性叫法修订。
7. 运行验证，生成 `K-000013` 候选版本。
8. 切换审核人员，查看与 `K-000012` 的差异。
9. 审核通过并发布。
10. 回到业务需求，看到“可使用新版本重新分析”，历史运行仍显示 `K-000012`。

## 核心对象

前端类型先固定未来后端边界：

- `UserProfile`
- `WorkspaceSummary`
- `TraceRequest`
- `TraceRun`
- `FieldResult`
- `Evidence`
- `ReviewTask`
- `Material`
- `KnowledgeDraft`
- `KnowledgeVersion`
- `Release`
- `AuditEvent`

每个 `TraceRun` 保存 `knowledgeVersionId`。每个 `FieldResult` 保存结果类型、定位状态、证据状态和来源引用。前端不以一个分数同时表达准确性、证据和人工确认。

## Mock service 契约

`product-demo/src/services/mockService.ts` 对外提供：

- `getSession()`
- `getWorkbenchSummary()`
- `listTraceRequests()`
- `getTraceRequest(id)`
- `createTraceRequest(input)`
- `submitTraceRun(requestId, input)`
- `submitFeedback(input)`
- `listReviewTasks()`
- `getKnowledgeOverview()`
- `listMaterials()`
- `getKnowledgeDraft()`
- `runValidation()`
- `listKnowledgeVersions()`
- `getVersionDiff(versionId)`
- `approveVersion(versionId)`
- `publishVersion(versionId)`
- `listAuditEvents()`

服务层使用内存状态并提供短暂的异步延迟；所有页面通过服务层访问状态。这样后续接真实 API 时只替换 service adapter。

## 状态与视觉原则

- 业务状态：已定位、需澄清、证据不足、范围未覆盖。
- 结果类型：直接映射、计算字段、分类规则。
- 证据状态：已核验、部分支持、存在冲突、已过期。
- 版本状态：草稿、构建中、待审核、已发布、已退回。
- 所有长任务显示当前阶段、任务编号和可恢复入口。
- 证据默认呈现业务可读信息，物理列、任务名和版本可复制。
- 不能以绿色状态暗示“高分就是正确”；状态和证据独立展示。
- 适配 1366px 以上工作台；窄屏让内容纵向收拢，表格在容器内滚动。
- 不使用 emoji 作为产品图标；采用文本图标或内联 SVG。

## 架构图内容

架构图使用中文主文案、保留代码标识和 API 名称，最多 12 个主节点：

1. 业务人员
2. 字段溯源前端
3. 知识工作台前端
4. FastAPI 产品 API
5. 查询服务与工具链
6. 构建/解析 Worker
7. 应用关系库
8. 材料与知识包存储
9. OntoWing 领域库
10. 源系统只读库
11. DataWorks/DDL/任务材料
12. 已发布知识版本

主路径：业务请求 → API → 已发布版本 → 语义索引/证据 → 字段来源清单。维护路径：材料/结构 → worker → OntoWing 验证 → 候选知识包 → 审核发布 → 线上版本指针。

## 验收

- `cd product-demo && npm install && npm run build` 成功。
- 能在浏览器中完成上述 10 步业务路径。
- 刷新页面后 mock 状态仍在当前 session 内可恢复；没有隐式跳回演示后端。
- 业务详情同时展示版本、字段状态、证据和待确认项。
- 建模人员可从反馈进入草稿和验证；审核人员可完成候选版本发布。
- 架构图通过 Archify showcase 校验和 deliver，输出独立 HTML。
- 现有项目全量测试不因新前端失败。
