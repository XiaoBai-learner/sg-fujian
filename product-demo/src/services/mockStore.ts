import {
  auditEvents,
  diff,
  draft,
  fieldResults,
  materials,
  releases,
  requests,
  reviewTasks,
  summary,
  traceRuns,
  users,
  validation,
  versions,
} from './mockData'
import type {
  AuditEvent,
  KnowledgeDraft,
  KnowledgeVersion,
  Material,
  Release,
  ReviewTask,
  TraceRequest,
  TraceRun,
  UserProfile,
  ValidationRun,
  VersionDiff,
  WorkbenchSummary,
} from '../domain/types'

export interface MockStore {
  currentUserId: string
  users: UserProfile[]
  summary: WorkbenchSummary
  requests: TraceRequest[]
  traceRuns: TraceRun[]
  materials: Material[]
  draft: KnowledgeDraft
  validation: ValidationRun
  versions: KnowledgeVersion[]
  releases: Release[]
  reviews: ReviewTask[]
  audit: AuditEvent[]
  diff: VersionDiff
}

export const store: MockStore = {
  currentUserId: 'u-analyst',
  users,
  summary,
  requests,
  traceRuns,
  materials,
  draft,
  validation,
  versions,
  releases,
  reviews: reviewTasks,
  audit: auditEvents,
  diff,
}

export function currentUser() {
  return store.users.find(user => user.id === store.currentUserId) || store.users[0]
}

export function findRequest(id: string) {
  return store.requests.find(request => request.id === id)
}

export function findRun(id: string) {
  return store.traceRuns.find(run => run.id === id)
}
