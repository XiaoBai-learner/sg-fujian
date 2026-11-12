# 字段溯源平台 · 1.0 产品原型

这是正式版产品的独立前端原型。它使用 mock service 模拟业务操作，用来先确认产品工作流和页面形态，再逐步替换为真实后端接口。

当前原型覆盖：

- 业务工作台、需求提交、字段来源清单和证据侧栏；
- 直接映射、计算字段、证据不足和待澄清状态；
- 字段反馈与复核队列；
- 材料、语义模型、验证与试问；
- 知识版本差异、审核和发布；
- 系统连接和审计记录。

## 运行

```bash
cd product-demo
npm install
npm run dev
```

默认地址为 <http://127.0.0.1:4180>。

构建检查：

```bash
npm run typecheck
npm run build
```

## 原型路径

- `/workbench`：业务工作台
- `/requests/new`：新建溯源需求
- `/requests/req-1206`：示例需求详情
- `/knowledge`：知识工作台
- `/knowledge/materials`：材料与结构
- `/knowledge/model`：语义模型
- `/knowledge/validation`：验证与试问
- `/knowledge/versions`：版本与发布
- `/admin/connections`：系统连接
- `/admin/audit`：审计记录

右上角“演示角色”可以切换业务人员、建模人员、审核人员和管理员，用于查看不同工作区和操作流程。切换只作用于原型会话，不是生产认证实现。

## 服务边界

页面只通过 `src/services/mockService.ts` 访问数据。领域对象位于 `src/domain/types.ts`，mock 状态位于 `src/services/mockStore.ts`。后端实现时，保持这些对象的版本和状态语义，把 service adapter 替换成真实 API。

一次完整演示路径：

1. 从工作台进入“欠费客户清单字段溯源”；
2. 点击“户号”和“欠费金额”查看实际来源、计算口径和逐跳证据；
3. 对“缴费渠道”提交错误反馈；
4. 切换建模人员进入知识工作台，查看草稿和验证；
5. 切换审核人员，在“版本与发布”审核并发布 `K-000013`；
6. 返回历史需求，确认原执行仍固定 `K-000012`。

## 架构图

目标产品架构图位于：

`../docs/architecture/sgtrace-v1-architecture.html`

源规格为同目录的 `sgtrace-v1-architecture.json`。架构图展示业务查询主路径、材料到知识发布路径、应用关系库、知识包存储和 OntoWing 领域库之间的关系。
