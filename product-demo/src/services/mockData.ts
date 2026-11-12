import type {
  AuditEvent,
  Evidence,
  FieldResult,
  KnowledgeDraft,
  KnowledgeVersion,
  Material,
  Release,
  ReviewTask,
  TraceRequest,
  TraceRun,
  UserProfile,
  ValidationRun,
  WorkbenchSummary,
} from '../domain/types'

export const users: UserProfile[] = [
  { id: 'u-analyst', name: '林晓岚', title: '营销业务人员', role: 'analyst', organization: '福州供电公司' },
  { id: 'u-modeler', name: '周明远', title: '数据建模人员', role: 'modeler', organization: '数字化部' },
  { id: 'u-reviewer', name: '陈思远', title: '领域审核人', role: 'reviewer', organization: '营销部' },
  { id: 'u-admin', name: '王工', title: '平台管理员', role: 'admin', organization: '数字化部' },
]

const source = (id: string, column: string, tableComment: string, fieldComment: string, role: 'actual_source' | 'equivalent' | 'input' | 'condition' | 'candidate'): NonNullable<FieldResult['actualSource']> => ({
  id, column, system: column.split('.')[0], tableComment, fieldComment, role,
})

const mappingEvidence = (id: string, summary: string, status: Evidence['status'] = 'verified'): Evidence => ({
  id, label: '本体与 R2RML 映射', status, summary, sourceType: 'mapping', sourceName: '营销域 K-000012 / mapping.r2rml.ttl',
})

const lineageEvidence = (id: string, summary: string, status: Evidence['status'] = 'verified'): Evidence => ({
  id, label: '页面与任务血缘', status, summary, sourceType: 'lineage', sourceName: 'DataWorks 任务：dws_yx_kh_qf_hz',
})

const directField = (id: string, label: string, column: string, comment: string, score: number, note = ''): FieldResult => ({
  id, label, locationStatus: 'located', resultKind: 'direct', evidenceStatus: 'verified', confidence: score,
  actualSource: source(`${id}-source`, column, '应收电费流水', comment, 'actual_source'),
  equivalents: [source(`${id}-eq`, 'yx186.C_CONS.CONS_NO', '用电客户', '用户编号', 'equivalent')],
  candidates: [], evidence: [
    mappingEvidence(`${id}-map`, `业务属性“${label}”绑定到 ${column}`),
    lineageEvidence(`${id}-lineage`, '页面供数表的字段沿任务 SQL 追到该源字段'),
  ], lineage: [
    { from: 'sgfj_dataplatform.ads_yx_kh_qf_hz.yhbh', to: 'sgfj_dataplatform.dwd_yx_df_ysmx.cons_no', action: '字段投影' },
    { from: 'sgfj_dataplatform.dwd_yx_df_ysmx.cons_no', to: column, action: '任务 JOIN', expression: 'cons_no' },
  ], note,
})

export const fieldResults: FieldResult[] = [
  directField('fr-cons-no', '户号', 'yx186.A_RCVBL_FLOW.CONS_NO', '用户编号', .96),
  directField('fr-cons-name', '用户名称', 'yx186.A_RCVBL_FLOW.CONS_NAME', '用户名称', .93),
  directField('fr-org', '供电单位', 'yx186.O_ORG.ORG_NAME', '单位名称', .91),
  directField('fr-contract-cap', '合同容量', 'yx186.C_CONS.CONTRACT_CAP', '合同容量(kVA)', .94),
  directField('fr-arrears-month', '欠费月数', 'yx186.A_RCVBL_FLOW.RCVBL_YM', '应收年月', .82, '结果是按未结清月份去重计数'),
  directField('fr-receivable', '应收金额', 'yx186.A_RCVBL_FLOW.RCVBL_AMT', '应收金额', .97),
  directField('fr-paid', '实收金额', 'yx186.A_RCVBL_FLOW.RCVED_AMT', '实收金额', .97),
  directField('fr-status', '客户状态', 'yx186.C_CONS.CONS_STATUS', '客户状态', .89),
  {
    id: 'fr-arrears',
    label: '欠费金额',
    locationStatus: 'located',
    resultKind: 'calculated',
    evidenceStatus: 'verified',
    confidence: .91,
    actualSource: source('fr-arrears-source', 'sgfj_dataplatform.dws_yx_kh_qf_hz.qfje', '客户欠费汇总', '欠费金额', 'actual_source'),
    equivalents: [],
    candidates: [],
    evidence: [
      mappingEvidence('fr-arrears-map', '中台加工指标沿来源口径展开为应收减实收'),
      { id: 'fr-arrears-rule', label: '计算口径', status: 'verified', summary: '应收金额 - 实收金额；仅统计未结清记录', sourceType: 'business_rule', sourceName: '营销域规则：欠费金额' },
    ],
    lineage: [
      { from: 'yx186.A_RCVBL_FLOW.RCVBL_AMT', to: 'sgfj_dataplatform.dwd_yx_df_ysmx.rcvbl_amt', action: '字段同步' },
      { from: 'yx186.A_RCVBL_FLOW.RCVED_AMT', to: 'sgfj_dataplatform.dwd_yx_df_ysmx.rcved_amt', action: '字段同步' },
      { from: 'dwd_yx_df_ysmx.rcvbl_amt / rcved_amt', to: 'dws_yx_kh_qf_hz.qfje', action: '指标计算', expression: 'SUM(rcvbl_amt - rcved_amt) WHERE settle_flag = 0' },
    ],
    calculation: {
      expression: 'SUM(RCVBL_AMT - RCVED_AMT)',
      grain: '按客户编号、账期汇总',
      filters: ['SETTLE_FLAG = 0（未结清）', '账期在当前查询范围内'],
      joins: ['按 CONS_NO 关联用电客户'],
    },
  },
  {
    id: 'fr-channel',
    label: '缴费渠道',
    locationStatus: 'needs_clarification',
    resultKind: 'direct',
    evidenceStatus: 'conflict',
    confidence: .48,
    actualSource: undefined,
    equivalents: [],
    candidates: [
      source('fr-channel-c1', 'yx186.A_PAY_FLOW.PAY_MODE', '缴费记录', '缴费方式', 'candidate'),
      source('fr-channel-c2', 'yx186.A_PAY_FLOW.CHANNEL_CODE', '缴费记录', '渠道编码', 'candidate'),
    ],
    evidence: [
      mappingEvidence('fr-channel-map', '词表将“缴费渠道”同时匹配到“缴费方式”和“渠道编码”', 'conflict'),
    ],
    lineage: [],
    note: '请确认页面显示的是业务方式名称，还是渠道编码。',
  },
  {
    id: 'fr-load-rate',
    label: '负荷率',
    locationStatus: 'out_of_scope',
    resultKind: 'calculated',
    evidenceStatus: 'partial',
    confidence: .27,
    actualSource: undefined,
    equivalents: [],
    candidates: [
      source('fr-load-rate-c1', 'cjxt.E_MP_POWER_CURVE.P', '负荷曲线点', '有功功率', 'candidate'),
      source('fr-load-rate-c2', 'yx186.C_CONS.CONTRACT_CAP', '用电客户', '合同容量', 'candidate'),
    ],
    evidence: [
      { id: 'fr-load-rate-gap', label: '血缘缺口', status: 'partial', summary: '已找到两个输入字段，但当前页面的统计周期和最大负荷口径未确认', sourceType: 'lineage', sourceName: '材料缺口 #MAT-024' },
    ],
    lineage: [],
    calculation: {
      expression: 'MAX(P) / CONTRACT_CAP',
      grain: '页面统计周期内按计量点',
      filters: ['需要确认最大负荷时间窗口'],
      joins: ['按计量点和客户关联'],
    },
    note: '该字段暂不进入已发布版本的确定性回答。',
  },
]

export const traceRuns: TraceRun[] = [{
  id: 'run-1206-01',
  requestId: 'req-1206',
  knowledgeVersionId: 'K-000012',
  status: 'completed',
  startedAt: '2026-11-12 09:18:12',
  completedAt: '2026-11-12 09:18:18',
  durationSeconds: 6.2,
  fieldResults,
  note: '本次结果固定使用营销域 K-000012。',
}]

export const requests: TraceRequest[] = [{
  id: 'req-1206',
  title: '欠费客户清单字段溯源',
  description: '请确认欠费客户清单里的字段分别来自哪个系统、哪张原表和原表字段。',
  system: '营销业务应用 / 数据中台',
  page: '客户服务 > 欠费客户清单',
  ocrText: '欠费客户清单\\n户号  用户名称  供电单位  合同容量  欠费月数  应收金额  实收金额  欠费金额  缴费渠道  负荷率',
  fields: fieldResults.map(field => field.label),
  status: 'needs_review',
  createdAt: '2026-11-12 09:18',
  createdBy: '林晓岚',
  latestRunId: 'run-1206-01',
  runIds: ['run-1206-01'],
  reviewTaskIds: ['review-1206-channel'],
}]

export const materials: Material[] = [
  { id: 'mat-ddl', category: 'ddl', name: '营销与采集源系统 DDL', source: '现场结构导出 · Oracle / 2026-11-10', status: 'ready', updatedAt: '2026-11-11 18:20', scope: 'yx186、cjxt、kf95598', coverage: 100, issueCount: 0, excerpt: '60 张表 · 1,284 个字段 · 38 个主键' },
  { id: 'mat-lineage', category: 'lineage', name: 'DataWorks 血缘导出', source: 'DataWorks 项目 marketing_prod', status: 'partial', updatedAt: '2026-11-11 17:42', scope: 'ODS → DWD → DWS → ADS', coverage: 84, issueCount: 17, excerpt: '已解析 257 条边 · 17 条边缺少来源命名空间' },
  { id: 'mat-task-sql', category: 'task_sql', name: '任务 SQL（本次导入 34 个）', source: 'DataWorks 任务代码包', status: 'ready', updatedAt: '2026-11-11 17:58', scope: '营销域加工任务', coverage: 91, issueCount: 3, excerpt: '31 个任务完整解析 · 3 个任务包含动态 SQL' },
  { id: 'mat-doc', category: 'business_doc', name: '营销域字段口径说明', source: '业务部共享文档 / 2026-Q4', status: 'parsing', updatedAt: '2026-11-12 08:50', scope: '欠费、缴费、客户服务', coverage: 62, issueCount: 6, excerpt: '待业务人员确认 6 条口径与 2 个阈值' },
]

export const draft: KnowledgeDraft = {
  id: 'draft-013',
  revision: 18,
  title: '营销域知识草稿 · 反馈修订',
  updatedAt: '2026-11-12 10:24',
  updatedBy: '周明远',
  dirty: true,
  concepts: 22,
  attributes: 124,
  relations: 49,
  rules: 9,
  pendingChanges: [
    { id: 'chg-channel', type: '同义叫法', label: '缴费渠道 / 缴费方式', detail: '增加页面上下文约束：欠费清单优先使用 PAY_MODE，明细页保留 CHANNEL_CODE 候选', status: 'unverified' },
    { id: 'chg-arrears', type: '计算口径', label: '欠费金额', detail: '补充 SETTLE_FLAG = 0 过滤条件及按客户、账期汇总粒度', status: 'accepted' },
    { id: 'chg-load', type: '血缘缺口', label: '负荷率', detail: '等待采集系统最大负荷任务 SQL，当前不发布确定性映射', status: 'conflict' },
  ],
  selectedAttribute: {
    label: '户号',
    definition: '供电营销业务中标识用电客户的业务编号。',
    aliases: ['用户编号', '客户编号', '客户号'],
    mapping: 'yx186.A_RCVBL_FLOW.CONS_NO · yx186.C_CONS.CONS_NO',
    usage: '页面实际来源优先由页面供数表和任务血缘决定；客户档案页与应收明细页来源可不同。',
    evidence: '本体属性 Consumer.consNo · R2RML 映射 · 2 条任务 SQL JOIN 证据',
  },
}

export const validation: ValidationRun = {
  id: 'validation-013',
  status: 'completed',
  startedAt: '2026-11-12 10:30:11',
  completedAt: '2026-11-12 10:30:19',
  checks: [
    { id: 'model', label: '本体结构校验', status: 'passed', detail: '概念、属性、关系结构符合 OntoWing 约束', count: 0 },
    { id: 'pipeline', label: '映射与键校验', status: 'passed', detail: '124 个属性映射、49 条关系映射通过', count: 0 },
    { id: 'rules', label: '规则与约束校验', status: 'warning', detail: '1 条规则引用了尚未确认的业务阈值', count: 1 },
    { id: 'evidence', label: '来源证据检查', status: 'warning', detail: '3 个任务 SQL 解析不完整，影响 4 个字段', count: 4 },
    { id: 'regression', label: '已审核案例回归', status: 'passed', detail: '68 个字段结果保持一致，2 个字段状态变为待确认', count: 0 },
  ],
  regression: { total: 70, passed: 68, changed: 2 },
  message: '候选版本可以提交审核，但必须在发布说明中列出 4 个受影响字段。',
}

export const versions: KnowledgeVersion[] = [
  { id: 'K-000012', label: '营销域 · 2026-11-11 发布版', status: 'published', createdAt: '2026-11-11 19:10', createdBy: '周明远', summary: { concepts: 21, attributes: 118, relations: 47, rules: 8, coverage: 88 }, sourceSnapshot: 'snapshot-20261111-01', affectedFields: [] },
  { id: 'K-000013', label: '营销域 · 反馈修订候选', status: 'review', createdAt: '2026-11-12 10:31', createdBy: '周明远', summary: { concepts: 22, attributes: 124, relations: 49, rules: 9, coverage: 91 }, sourceSnapshot: 'snapshot-20261111-01 + draft-013', validationId: 'validation-013', affectedFields: ['缴费渠道', '欠费金额', '负荷率'], reviewNote: '补充计算字段口径，增加缴费方式页面上下文约束；负荷率继续保留证据缺口。' },
  { id: 'K-000011', label: '营销域 · 2026-11-07 发布版', status: 'rejected', createdAt: '2026-11-07 16:02', createdBy: '周明远', summary: { concepts: 21, attributes: 116, relations: 46, rules: 8, coverage: 84 }, sourceSnapshot: 'snapshot-20261107-02', affectedFields: ['欠费金额'], reviewNote: '欠费金额缺少过滤条件，退回补充。' },
]

export const releases: Release[] = [
  { id: 'rel-012', versionId: 'K-000012', releasedAt: '2026-11-11 19:10', releasedBy: '陈思远', reason: '首批营销域页面上线', previousVersionId: 'K-000010' },
]

export const reviewTasks: ReviewTask[] = [
  { id: 'review-1206-channel', type: 'answer_feedback', title: '反馈：缴费渠道定位不准确', summary: '业务人员认为“缴费渠道”应展示缴费方式名称，而不是渠道编码。', status: 'open', priority: 'high', requestId: 'req-1206', fieldResultId: 'fr-channel', draftId: 'draft-013', assignee: '周明远', updatedAt: '2026-11-12 09:42' },
  { id: 'review-release-013', type: 'release', title: '候选版本 K-000013 待审核', summary: '包含 3 个字段结果变化，验证通过但仍有 2 项提示。', status: 'in_progress', priority: 'normal', versionId: 'K-000013', assignee: '陈思远', updatedAt: '2026-11-12 10:34' },
]

export const auditEvents: AuditEvent[] = [
  { id: 'audit-1', action: '提交字段反馈', actor: '林晓岚', object: 'req-1206 / 缴费渠道', version: 'K-000012', at: '2026-11-12 09:42', detail: '标记为不正确，等待复核' },
  { id: 'audit-2', action: '保存知识草稿', actor: '周明远', object: 'draft-013 / 缴费渠道', at: '2026-11-12 10:24', detail: '增加页面上下文约束' },
  { id: 'audit-3', action: '运行版本验证', actor: '周明远', object: 'K-000013', version: 'K-000013', at: '2026-11-12 10:30', detail: '5 类检查完成，2 条提示' },
  { id: 'audit-4', action: '发布知识版本', actor: '陈思远', object: 'K-000012', version: 'K-000012', at: '2026-11-11 19:10', detail: '首批营销域页面上线' },
]

export const summary: WorkbenchSummary = {
  latestVersion: versions[0],
  openReviews: 2,
  knowledgeCoverage: 88,
  requestCounts: { total: 14, completed: 10, needsReview: 2 },
  materialHealth: { ready: 2, issues: 2, total: 4 },
  alerts: [
    { id: 'alert-review', tone: 'amber', title: '有 2 项复核任务待处理', detail: '缴费渠道反馈和 K-000013 候选版本需要继续处理。', href: '/knowledge' },
    { id: 'alert-material', tone: 'red', title: '任务 SQL 有 3 个解析缺口', detail: '影响负荷率等 4 个字段的确定性回答。', href: '/knowledge/materials' },
  ],
}

export const diff = {
  current: versions[0],
  candidate: versions[1],
  changes: [
    { type: 'changed' as const, label: '缴费渠道', detail: '新增“缴费方式”页面上下文约束，候选来源从单一列改为按页面场景选择。', affected: ['欠费客户清单', '缴费明细'] },
    { type: 'changed' as const, label: '欠费金额', detail: '补充应收减实收表达式、未结清过滤和客户/账期粒度。', affected: ['欠费客户清单'] },
    { type: 'blocked' as const, label: '负荷率', detail: '仍缺少最大负荷时间窗口，继续标记为证据不足。', affected: ['客户负荷分析'] },
    { type: 'added' as const, label: '客户服务事件规则', detail: '新增投诉客户与重点关注客户的规则链说明。', affected: ['重点关注客户'] },
  ],
}
