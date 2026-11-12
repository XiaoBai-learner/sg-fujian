import type {
  FeedbackInput,
  KnowledgeDraft,
  KnowledgeOverview,
  KnowledgeVersion,
  Material,
  NewRequestInput,
  Release,
  ReviewTask,
  Session,
  TraceRequest,
  TraceRun,
  UserProfile,
  ValidationRun,
  VersionDiff,
  WorkbenchSummary,
} from '../domain/types'
import { fieldResults } from './mockData'
import { currentUser, findRequest, findRun, store } from './mockStore'

const wait = (ms = 260) => new Promise(resolve => window.setTimeout(resolve, ms))

export async function getSession(): Promise<Session> {
  await wait(120)
  return { user: currentUser(), environment: '测试环境', domain: '营销域', latestVersionId: store.summary.latestVersion.id }
}

export async function setDemoUser(userId: string): Promise<Session> {
  await wait(100)
  if (store.users.some(user => user.id === userId)) store.currentUserId = userId
  return getSession()
}

export async function getWorkbenchSummary(): Promise<WorkbenchSummary> {
  await wait()
  return structuredClone(store.summary)
}

export async function listTraceRequests(): Promise<TraceRequest[]> {
  await wait()
  return structuredClone(store.requests)
}

export async function getTraceRequest(id: string): Promise<{ request: TraceRequest; run: TraceRun }> {
  await wait()
  const request = findRequest(id)
  if (!request) throw new Error('找不到这条需求')
  const run = findRun(request.latestRunId)
  if (!run) throw new Error('这条需求尚未生成执行结果')
  return structuredClone({ request, run })
}

export async function createTraceRequest(input: NewRequestInput): Promise<TraceRequest> {
  await wait(420)
  const id = `req-${Date.now().toString(36)}`
  const runId = `run-${Date.now().toString(36)}`
  const request: TraceRequest = {
    id, title: input.title || '未命名字段溯源需求', description: input.description, system: input.system,
    page: input.page, ocrText: input.ocrText, fields: input.fields, status: 'running',
    createdAt: new Date().toISOString().slice(0, 16).replace('T', ' '), createdBy: currentUser().name,
    latestRunId: runId, runIds: [runId], reviewTaskIds: [],
  }
  const run: TraceRun = {
    id: runId, requestId: id, knowledgeVersionId: store.summary.latestVersion.id, status: 'running',
    startedAt: new Date().toISOString().slice(0, 16).replace('T', ' '), fieldResults: [],
  }
  store.requests.unshift(request)
  store.traceRuns.unshift(run)
  window.setTimeout(() => {
    const item = findRequest(id)
    const current = findRun(runId)
    if (!item || !current) return
    current.status = 'completed'
    current.completedAt = new Date().toISOString().slice(0, 16).replace('T', ' ')
    current.durationSeconds = 3.8
    current.fieldResults = input.fields.map((label, index) => {
      const known = fieldResults.find(field => field.label === label)
      return known ? structuredClone(known) : {
        id: `${runId}-field-${index}`, label, locationStatus: 'insufficient_evidence' as const,
        resultKind: 'direct' as const, evidenceStatus: 'partial' as const, confidence: .18,
        equivalents: [], candidates: [], evidence: [], lineage: [], note: '当前知识版本没有覆盖这个字段。',
      }
    })
    item.status = 'completed'
    store.summary.requestCounts.total += 1
    store.summary.requestCounts.completed += 1
  }, 1100)
  return structuredClone(request)
}

export async function getRun(requestId: string): Promise<TraceRun> {
  await wait(180)
  const request = findRequest(requestId)
  if (!request) throw new Error('找不到这条需求')
  const run = findRun(request.latestRunId)
  if (!run) throw new Error('找不到执行记录')
  return structuredClone(run)
}

export async function submitTraceRun(requestId: string): Promise<TraceRun> {
  await wait(520)
  return getRun(requestId)
}

export async function submitFeedback(input: FeedbackInput): Promise<ReviewTask> {
  await wait(360)
  const request = findRequest(input.requestId)
  const task: ReviewTask = {
    id: `review-${Date.now().toString(36)}`, type: 'answer_feedback',
    title: `反馈：${input.verdict === 'wrong' ? '字段定位不准确' : '需要补充页面上下文'}`,
    summary: input.reason || '业务人员提交了字段结果反馈。',
    status: 'open', priority: 'high', requestId: input.requestId, fieldResultId: input.fieldResultId,
    draftId: store.draft.id, assignee: '周明远', updatedAt: new Date().toISOString().slice(0, 16).replace('T', ' '),
  }
  store.reviews.unshift(task)
  if (request) {
    request.status = 'needs_review'
    request.reviewTaskIds.unshift(task.id)
  }
  store.summary.openReviews += 1
  store.audit.unshift({ id: `audit-${Date.now().toString(36)}`, action: '提交字段反馈', actor: currentUser().name, object: `${input.requestId} / ${input.fieldResultId}`, version: store.summary.latestVersion.id, at: task.updatedAt, detail: task.summary })
  return structuredClone(task)
}

export async function listReviewTasks(): Promise<ReviewTask[]> {
  await wait()
  return structuredClone(store.reviews)
}

export async function getKnowledgeOverview(): Promise<KnowledgeOverview> {
  await wait()
  return structuredClone({
    latestVersion: store.summary.latestVersion, draft: store.draft, validation: store.validation,
    materialHealth: store.summary.materialHealth, openReviews: store.reviews.filter(review => review.status !== 'resolved'),
    conflicts: store.draft.pendingChanges.filter(change => change.status === 'conflict').map(change => ({ id: change.id, label: change.label, detail: change.detail, affected: ['负荷率'] })),
  })
}

export async function listMaterials(): Promise<Material[]> {
  await wait()
  return structuredClone(store.materials)
}

export async function getKnowledgeDraft(): Promise<KnowledgeDraft> {
  await wait()
  return structuredClone(store.draft)
}

export async function runValidation(): Promise<ValidationRun> {
  store.validation.status = 'running'
  await wait(850)
  store.validation.status = 'completed'
  store.validation.completedAt = new Date().toISOString().slice(0, 16).replace('T', ' ')
  store.audit.unshift({ id: `audit-${Date.now().toString(36)}`, action: '运行版本验证', actor: currentUser().name, object: 'K-000013', version: 'K-000013', at: store.validation.completedAt, detail: store.validation.message })
  return structuredClone(store.validation)
}

export async function listKnowledgeVersions(): Promise<KnowledgeVersion[]> {
  await wait()
  return structuredClone(store.versions)
}

export async function getVersionDiff(versionId: string): Promise<VersionDiff> {
  await wait()
  if (versionId !== store.diff.candidate.id) return structuredClone({ ...store.diff, candidate: store.versions.find(version => version.id === versionId) || store.diff.candidate })
  return structuredClone(store.diff)
}

export async function approveVersion(versionId: string): Promise<KnowledgeVersion> {
  await wait(420)
  const version = store.versions.find(item => item.id === versionId)
  if (!version) throw new Error('找不到候选版本')
  version.status = 'review'
  version.reviewNote = '审核通过，等待发布。'
  const task = store.reviews.find(item => item.versionId === versionId)
  if (task) { task.status = 'resolved'; task.updatedAt = new Date().toISOString().slice(0, 16).replace('T', ' ') }
  const at = new Date().toISOString().slice(0, 16).replace('T', ' ')
  store.audit.unshift({ id: `audit-${Date.now().toString(36)}`, action: '审核通过', actor: currentUser().name, object: versionId, version: versionId, at, detail: '审核人确认候选版本可发布' })
  return structuredClone(version)
}

export async function publishVersion(versionId: string): Promise<{ version: KnowledgeVersion; release: Release }> {
  await wait(500)
  const target = store.versions.find(version => version.id === versionId)
  if (!target) throw new Error('找不到候选版本')
  const previous = store.summary.latestVersion
  target.status = 'published'
  previous.status = 'superseded'
  const release: Release = {
    id: `rel-${Date.now().toString(36)}`, versionId, releasedAt: new Date().toISOString().slice(0, 16).replace('T', ' '),
    releasedBy: currentUser().name, reason: '审核通过后发布候选版本', previousVersionId: previous.id,
  }
  store.releases.unshift(release)
  store.summary.latestVersion = target
  store.summary.openReviews = Math.max(0, store.summary.openReviews - 1)
  store.audit.unshift({ id: `audit-${Date.now().toString(36)}`, action: '发布知识版本', actor: currentUser().name, object: versionId, version: versionId, at: release.releasedAt, detail: release.reason })
  return structuredClone({ version: target, release })
}

export async function listAuditEvents() {
  await wait()
  return structuredClone(store.audit)
}

export function availableUsers() {
  return structuredClone(store.users)
}

export function currentFieldResult(fieldId: string) {
  const run = findRun('run-1206-01')
  return run?.fieldResults.find(field => field.id === fieldId)
}
