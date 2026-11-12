export type Role = 'analyst' | 'modeler' | 'reviewer' | 'admin'
export type LocationStatus = 'located' | 'needs_clarification' | 'insufficient_evidence' | 'out_of_scope'
export type ResultKind = 'direct' | 'calculated' | 'rule'
export type EvidenceStatus = 'verified' | 'partial' | 'conflict' | 'stale'
export type VersionStatus = 'draft' | 'building' | 'review' | 'published' | 'superseded' | 'rejected'
export type MaterialStatus = 'ready' | 'parsing' | 'partial' | 'failed'
export type ReviewStatus = 'open' | 'in_progress' | 'resolved' | 'rejected'

export type Tone = 'green' | 'amber' | 'red' | 'blue' | 'gold' | 'neutral' | 'purple'

export interface UserProfile {
  id: string
  name: string
  title: string
  role: Role
  organization: string
}

export interface SourceReference {
  id: string
  column: string
  system: string
  tableComment: string
  fieldComment: string
  role: 'actual_source' | 'equivalent' | 'input' | 'condition' | 'candidate'
}

export interface Evidence {
  id: string
  label: string
  status: EvidenceStatus
  summary: string
  sourceType: 'mapping' | 'lineage' | 'task_sql' | 'metadata' | 'business_rule' | 'value_check'
  sourceName: string
  location?: string
  detail?: string
}

export interface LineageStep {
  from: string
  to: string
  action: string
  expression?: string
}

export interface Calculation {
  expression: string
  grain: string
  filters: string[]
  joins: string[]
}

export interface FieldResult {
  id: string
  label: string
  locationStatus: LocationStatus
  resultKind: ResultKind
  evidenceStatus: EvidenceStatus
  confidence: number
  actualSource?: SourceReference
  equivalents: SourceReference[]
  candidates: SourceReference[]
  evidence: Evidence[]
  lineage: LineageStep[]
  calculation?: Calculation
  note?: string
}

export interface TraceRun {
  id: string
  requestId: string
  knowledgeVersionId: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  startedAt: string
  completedAt?: string
  durationSeconds?: number
  fieldResults: FieldResult[]
  note?: string
}

export interface TraceRequest {
  id: string
  title: string
  description: string
  system: string
  page: string
  ocrText: string
  fields: string[]
  status: 'draft' | 'running' | 'completed' | 'needs_review'
  createdAt: string
  createdBy: string
  latestRunId: string
  runIds: string[]
  reviewTaskIds: string[]
}

export interface ReviewTask {
  id: string
  type: 'answer_feedback' | 'knowledge_change' | 'release'
  title: string
  summary: string
  status: ReviewStatus
  priority: 'high' | 'normal' | 'low'
  requestId?: string
  fieldResultId?: string
  draftId?: string
  versionId?: string
  assignee: string
  updatedAt: string
}

export interface Material {
  id: string
  category: 'ddl' | 'lineage' | 'task_sql' | 'business_doc'
  name: string
  source: string
  status: MaterialStatus
  updatedAt: string
  scope: string
  coverage: number
  issueCount: number
  excerpt: string
}

export interface KnowledgeDraft {
  id: string
  revision: number
  title: string
  updatedAt: string
  updatedBy: string
  dirty: boolean
  concepts: number
  attributes: number
  relations: number
  rules: number
  pendingChanges: { id: string; type: string; label: string; detail: string; status: 'unverified' | 'conflict' | 'accepted' }[]
  selectedAttribute: {
    label: string
    definition: string
    aliases: string[]
    mapping: string
    usage: string
    evidence: string
  }
}

export interface ValidationRun {
  id: string
  status: 'idle' | 'running' | 'completed' | 'failed'
  startedAt: string
  completedAt?: string
  checks: { id: string; label: string; status: 'passed' | 'warning' | 'failed'; detail: string; count?: number }[]
  regression: { total: number; passed: number; changed: number }
  message: string
}

export interface KnowledgeVersion {
  id: string
  label: string
  status: VersionStatus
  createdAt: string
  createdBy: string
  summary: { concepts: number; attributes: number; relations: number; rules: number; coverage: number }
  sourceSnapshot: string
  validationId?: string
  affectedFields: string[]
  reviewNote?: string
}

export interface Release {
  id: string
  versionId: string
  releasedAt: string
  releasedBy: string
  reason: string
  previousVersionId?: string
}

export interface AuditEvent {
  id: string
  action: string
  actor: string
  object: string
  version?: string
  at: string
  detail: string
}

export interface WorkbenchSummary {
  latestVersion: KnowledgeVersion
  openReviews: number
  knowledgeCoverage: number
  requestCounts: { total: number; completed: number; needsReview: number }
  materialHealth: { ready: number; issues: number; total: number }
  alerts: { id: string; tone: Tone; title: string; detail: string; href: string }[]
}

export interface KnowledgeOverview {
  latestVersion: KnowledgeVersion
  draft: KnowledgeDraft
  validation: ValidationRun
  materialHealth: { ready: number; issues: number; total: number }
  openReviews: ReviewTask[]
  conflicts: { id: string; label: string; detail: string; affected: string[] }[]
}

export interface VersionDiff {
  current: KnowledgeVersion
  candidate: KnowledgeVersion
  changes: { type: 'added' | 'changed' | 'blocked' | 'removed'; label: string; detail: string; affected: string[] }[]
}

export interface FeedbackInput {
  requestId: string
  fieldResultId: string
  verdict: 'correct' | 'wrong' | 'needs_context'
  reason: string
  correction?: string
}

export interface NewRequestInput {
  title: string
  description: string
  system: string
  page: string
  ocrText: string
  fields: string[]
}

export interface Session {
  user: UserProfile
  environment: '测试环境'
  domain: '营销域'
  latestVersionId: string
}
