# Standalone 1.0 Product Demo Implementation Plan

> 历史方案：2026-11-16 用户将产品收敛为“数据源接入 → OntoWing 本体建模 → 字段溯源智能体”，所有人使用同一套功能。本文件中的角色分工、需求工单和审核发布工作台已废弃；以 `docs/superpowers/specs/2026-11-16-lightweight-product.md` 为准。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an independent, mock-driven React product frontend that demonstrates the real 1.0 trace-to-review-to-release workflow, plus a validated standalone architecture diagram.

**Architecture:** `product-demo/` is a separate Vite application with its own shell, route state, domain types, mock service, and pages. Pages depend on the mock service contract rather than the current `/api/app/*` demo endpoints, so the service adapter can later be replaced by real backend calls. The architecture artifact is authored as Archify JSON and delivered as a self-contained HTML file under `docs/architecture/`.

**Tech Stack:** React 18, TypeScript, Vite, CSS modules-by-convention in one product stylesheet, Archify JSON/HTML; no new runtime backend dependencies.

**Spec:** `docs/superpowers/specs/2026-11-12-product-demo-design.md`

## Global Constraints

- Preserve the existing `frontend/` demo and all current `sgtrace/` tests.
- Keep the new frontend independent from `/api/app/*`; all pages call `src/services/mockService.ts`.
- Use explicit result states: location, result type, evidence, and human review remain separate.
- Use a dense enterprise workbench layout, visible focus states, keyboard-accessible controls, and no emoji product icons.
- Keep the core prototype flow operable: request → field evidence → feedback → draft → validation → approval → release.
- Architecture diagram authored in Chinese with exact product/API identifiers preserved and validated with Archify showcase quality.

### Task 1: Scaffold the independent product frontend

**Files:**
- Create: `product-demo/package.json`
- Create: `product-demo/tsconfig.json`
- Create: `product-demo/vite.config.ts`
- Create: `product-demo/index.html`
- Create: `product-demo/src/main.tsx`
- Create: `product-demo/src/styles.css`
- Create: `product-demo/public/sgtrace-mark.svg`

**Interfaces:**
- Produces a standalone Vite app runnable with `npm install` and `npm run build`.
- `main.tsx` mounts `ProductDemoApp` from `src/App.tsx`.

- [ ] **Step 1: Add the package and TypeScript configuration**

Use React 18 and the existing repository TypeScript/Vite version family:

```json
{
  "name": "sgtrace-product-demo",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/react": "18.3.18",
    "@types/react-dom": "18.3.5",
    "@vitejs/plugin-react": "4.3.4",
    "typescript": "5.7.3",
    "vite": "6.4.3"
  }
}
```

- [ ] **Step 2: Add the entrypoint, Vite config, and HTML title**

`main.tsx` imports `styles.css`, mounts `ProductDemoApp` into `#root`, and `index.html` uses the title `字段溯源平台 · 1.0 产品原型`.

- [ ] **Step 3: Add the base style tokens and mark**

Define local CSS variables for navy, slate, gold, green, amber, red, borders, spacing, radii, typography, and focus rings. Add responsive rules for 1366px workstations and a single-column narrow layout. The mark is an inline-safe SVG asset with the Chinese character `溯`.

- [ ] **Step 4: Run the initial build**

Run: `cd product-demo && npm install && npm run build`

Expected: Vite emits `dist/` with exit code 0.

- [ ] **Step 5: Commit the scaffold**

```bash
git add product-demo
git commit -m "feat: scaffold standalone product frontend"
```

### Task 2: Define domain types and the mock service

**Files:**
- Create: `product-demo/src/domain/types.ts`
- Create: `product-demo/src/services/mockData.ts`
- Create: `product-demo/src/services/mockService.ts`
- Create: `product-demo/src/services/mockStore.ts`

**Interfaces:**
- `ProductDemoApp` consumes `getSession`, `getWorkbenchSummary`, `listTraceRequests`, `getTraceRequest`, `submitFeedback`, `listReviewTasks`, `getKnowledgeOverview`, `listMaterials`, `getKnowledgeDraft`, `runValidation`, `listKnowledgeVersions`, `getVersionDiff`, `approveVersion`, `publishVersion`, and `listAuditEvents`.
- Services return `Promise<T>` and add 180–420ms delay. Mutations update the in-memory store so navigation between pages demonstrates state changes.

- [ ] **Step 1: Define the domain types**

Define discriminated unions for:

```ts
export type LocationStatus = 'located' | 'needs_clarification' | 'insufficient_evidence' | 'out_of_scope'
export type ResultKind = 'direct' | 'calculated' | 'rule'
export type EvidenceStatus = 'verified' | 'partial' | 'conflict' | 'stale'
export type VersionStatus = 'draft' | 'building' | 'review' | 'published' | 'rejected'
```

Add `UserProfile`, `TraceRequest`, `TraceRun`, `FieldResult`, `Evidence`, `ReviewTask`, `Material`, `KnowledgeDraft`, `KnowledgeVersion`, `Release`, `AuditEvent`, and summary types. `TraceRun` must include `knowledgeVersionId`; `FieldResult` must include `locationStatus`, `resultKind`, `evidenceStatus`, `confidence`, `sources`, `evidence`, and optional `calculation`.

- [ ] **Step 2: Create representative mock data**

Create the “欠费客户清单字段溯源” request with 11 fields: 8 located, 2 needing clarification, and 1 out of scope. Include detailed evidence for `户号` and `欠费金额`, a conflict for `缴费渠道`, and a review task linked to the feedback.

Create `K-000012` as published, `K-000013` as a draft/review candidate, four materials with mixed parse states, one validation report with one warning, and audit events for feedback, validation, and release.

- [ ] **Step 3: Implement the store and service methods**

Use a module-level store initialized from `mockData`. Mutating methods must update the same store object:

```ts
export async function submitFeedback(input: FeedbackInput): Promise<ReviewTask>
export async function runValidation(): Promise<ValidationRun>
export async function approveVersion(versionId: string): Promise<KnowledgeVersion>
export async function publishVersion(versionId: string): Promise<Release>
```

`publishVersion` marks the target version published, retains the old release in history, and changes the summary’s `latestVersionId`; it must never mutate existing `TraceRun.knowledgeVersionId`.

- [ ] **Step 4: Typecheck the service layer**

Run: `cd product-demo && npm run typecheck`

Expected: PASS with no TypeScript diagnostics.

- [ ] **Step 5: Commit the domain layer**

```bash
git add product-demo/src/domain product-demo/src/services
git commit -m "feat: add product demo domain and mock service"
```

### Task 3: Build the product shell and role navigation

**Files:**
- Create: `product-demo/src/App.tsx`
- Create: `product-demo/src/components/AppShell.tsx`
- Create: `product-demo/src/components/StatusBadge.tsx`
- Create: `product-demo/src/components/MetricCard.tsx`
- Create: `product-demo/src/components/EmptyState.tsx`
- Create: `product-demo/src/components/AsyncState.tsx`

**Interfaces:**
- `AppShell` accepts `{ session, activePath, onNavigate, children }`.
- `StatusBadge` accepts `{ label, tone }`, where tone is a closed union.
- App routing is a small pathname switch with local navigation, not a dependency on React Router.

- [ ] **Step 1: Add role-aware navigation**

Provide role switcher options `analyst`, `modeler`, `reviewer`, and `admin`. Render product sections based on role, but let the prototype switch roles from the top-right “演示角色” control. The shell must show current domain, environment, current knowledge version, and user identity.

- [ ] **Step 2: Add the route map**

Implement these paths:

```ts
const routes = [
  '/workbench',
  '/requests/new',
  '/requests/:id',
  '/knowledge',
  '/knowledge/materials',
  '/knowledge/model',
  '/knowledge/validation',
  '/knowledge/versions',
  '/admin/connections',
  '/admin/audit',
]
```

For unknown paths, render a recoverable 404 state with a link back to `/workbench`.

- [ ] **Step 3: Add shared shell styles**

Implement dense sidebar navigation, top context bar, breadcrumb/title row, page actions, status chips, loading/error/empty states, and keyboard-visible focus. Keep the main content width between 1180px and 1500px.

- [ ] **Step 4: Add a smoke home view**

Render a temporary workbench placeholder from `/workbench` so the shell is testable before feature pages are added.

- [ ] **Step 5: Run build and commit**

Run: `cd product-demo && npm run build`

Expected: PASS.

```bash
git add product-demo/src/App.tsx product-demo/src/components product-demo/src/styles.css
git commit -m "feat: add product workbench shell"
```

### Task 4: Implement the business trace workflow

**Files:**
- Create: `product-demo/src/pages/WorkbenchPage.tsx`
- Create: `product-demo/src/pages/NewRequestPage.tsx`
- Create: `product-demo/src/pages/RequestDetailPage.tsx`
- Create: `product-demo/src/components/RequestTable.tsx`
- Create: `product-demo/src/components/FieldResultTable.tsx`
- Create: `product-demo/src/components/EvidencePanel.tsx`
- Create: `product-demo/src/components/FeedbackDialog.tsx`

**Interfaces:**
- Pages use only `mockService` methods and domain types.
- `FieldResultTable` calls `onSelect(resultId)` and renders independent location/result/evidence states.
- `EvidencePanel` accepts a `FieldResult` and shows page context, mapping, lineage, expression/conditions, evidence source, and knowledge version.

- [ ] **Step 1: Implement the workbench summary**

Show current published version, “待处理” count, knowledge coverage, recent requests, and the review alert. The request table links each row to `/requests/:id`.

- [ ] **Step 2: Implement the new request form**

Use labeled controls for title, description, system/page context, OCR text, and fields. Pre-fill the sample request option for review. On submit, call `createTraceRequest` and navigate to the new request detail.

- [ ] **Step 3: Implement the request detail layout**

Use three zones: request/run context, field result table, and evidence detail panel. Render a version banner that says the run is fixed to its knowledge version. Add “重新分析” and “提交复核” actions with explicit state updates.

- [ ] **Step 4: Implement field result details**

For direct results show the actual page source and related equivalent fields. For calculated results show formula, input fields, filters, joins, and grain. For unresolved results show known candidates and the exact evidence gap. Never show an unresolved candidate as a confirmed source.

- [ ] **Step 5: Implement feedback**

Clicking “不正确” opens a dialog requiring a reason and allowing an optional correction. The submit action calls `submitFeedback`, closes the dialog, and updates the request with a visible review status.

- [ ] **Step 6: Build and smoke the complete business flow**

Run: `cd product-demo && npm run build`

Then run the app with `npm run dev -- --host 127.0.0.1` and verify the route path, request details, evidence expansion, feedback dialog, and role switcher in a browser.

- [ ] **Step 7: Commit the business workflow**

```bash
git add product-demo/src/pages product-demo/src/components
git commit -m "feat: add business trace workflow"
```

### Task 5: Implement knowledge, review, release, and admin workflows

**Files:**
- Create: `product-demo/src/pages/KnowledgeOverviewPage.tsx`
- Create: `product-demo/src/pages/MaterialsPage.tsx`
- Create: `product-demo/src/pages/KnowledgeModelPage.tsx`
- Create: `product-demo/src/pages/ValidationPage.tsx`
- Create: `product-demo/src/pages/VersionsPage.tsx`
- Create: `product-demo/src/pages/ConnectionsPage.tsx`
- Create: `product-demo/src/pages/AuditPage.tsx`
- Create: `product-demo/src/components/VersionDiff.tsx`
- Create: `product-demo/src/components/ReviewQueue.tsx`
- Create: `product-demo/src/components/KnowledgeTabs.tsx`

**Interfaces:**
- Pages consume the knowledge and admin service methods from Task 2.
- `VersionDiff` accepts `{ current, candidate }` and groups additions, changes, conflicts, and affected fields.
- `ReviewQueue` accepts `ReviewTask[]` and links feedback to the relevant request and draft change.

- [ ] **Step 1: Build the knowledge overview**

Show published version, draft status, material health, unresolved conflicts, review queue, and the latest release event. Link each action to its detail page.

- [ ] **Step 2: Build the materials page**

Show materials by category, parse status, coverage, source, last update, and unresolved parse issues. Use a detail drawer for a material’s affected tables/fields and source excerpt.

- [ ] **Step 3: Build the knowledge model page**

Show concept/attribute/relation/rule tabs; provide a selected attribute detail with accepted labels, physical mappings, page usage, evidence, and a small editable draft control. Saving updates the mock draft and adds a “未验证修改” marker.

- [ ] **Step 4: Build validation and trial query**

Show validation categories and results. `runValidation()` transitions from idle to running to completed, reveals the warning, and updates candidate version status. Add a trial query panel that displays the same result state model as business queries.

- [ ] **Step 5: Build versions and release**

Show draft/candidate/published/rejected versions. Selecting `K-000013` displays the diff against `K-000012`, validation result, affected fields, and review actions. `approveVersion` then enables `publishVersion`. Publishing updates the shell version and the overview while preserving old runs.

- [ ] **Step 6: Build connections and audit**

Show registered systems, source type, snapshot status, table count, and last collection. Audit page filters by action and displays operator, object, version, and time; do not show OCR body or credentials.

- [ ] **Step 7: Build and smoke the knowledge flow**

Run: `cd product-demo && npm run build`

Verify role switch → feedback queue → draft → validation → version diff → approve → publish → old request version remains unchanged.

- [ ] **Step 8: Commit**

```bash
git add product-demo/src/pages product-demo/src/components
git commit -m "feat: add knowledge review and release workflows"
```

### Task 6: Author and validate the architecture diagram

**Files:**
- Create: `docs/architecture/sgtrace-v1-architecture.json`
- Create: `docs/architecture/sgtrace-v1-architecture.html`

**Interfaces:**
- The JSON is the source specification for the delivered HTML.
- The HTML is standalone and includes inline SVG/runtime from Archify.

- [ ] **Step 1: Read the architecture schema and example**

Read the Archify architecture schema, common schema, and one architecture example from the installed skill. Use the repository facts and the design spec as the content source.

- [ ] **Step 2: Author the candidate JSON**

Use at most 12 primary nodes and one obvious main path. Include product frontend, knowledge frontend, API, query/tool service, worker, app DB, artifact storage, OntoWing, source DB, material inputs, and published version. Use semantic edge labels such as “提交需求”, “固定版本检索”, “生成候选包”, “审核发布”.

- [ ] **Step 3: Validate and deliver**

Run:

```bash
node /Users/wangchunyu/.codex/skills/archify/bin/archify.mjs validate architecture docs/architecture/sgtrace-v1-architecture.json --quality showcase --json
node /Users/wangchunyu/.codex/skills/archify/bin/archify.mjs deliver architecture docs/architecture/sgtrace-v1-architecture.json docs/architecture/sgtrace-v1-architecture.html --quality showcase --json
```

Expected: 9 showcase artifact checks, 0 composition errors, 0 warnings, and a delivered HTML path with a SHA-256 receipt.

- [ ] **Step 4: Run bounded visual containment checks**

Run:

```bash
node /Users/wangchunyu/.codex/skills/archify/bin/archify.mjs visual-check docs/architecture/sgtrace-v1-architecture.html --json
```

Report the tool’s truthful `visualReview` status; do not claim visual polish without inspecting screenshots.

- [ ] **Step 5: Commit the architecture artifact**

```bash
git add docs/architecture
git commit -m "docs: add 1.0 product architecture diagram"
```

### Task 7: Document usage and run final verification

**Files:**
- Create: `product-demo/README.md`
- Modify: `README.md` if it exists; otherwise do not create a repository-wide README solely for this task.

**Interfaces:**
- README documents the exact commands to install, run, build, and inspect the architecture artifact.

- [ ] **Step 1: Write product demo usage**

Document:

```bash
cd product-demo
npm install
npm run dev
npm run build
```

Include the route list, demo role switcher behavior, mock service boundary, and the planned replacement point for real API adapters.

- [ ] **Step 2: Run frontend build**

Run: `cd product-demo && npm run build`

Expected: PASS.

- [ ] **Step 3: Run existing backend tests**

Run: `.venv/bin/python -m pytest -q`

Expected: all existing tests pass; the new frontend must not change the count or behavior.

- [ ] **Step 4: Check repository diff**

Run: `git diff --check` and `git status --short --branch`.

Expected: no whitespace errors; all new product-demo and architecture files are visible, with pre-existing worktree changes preserved.

- [ ] **Step 5: Commit documentation**

```bash
git add product-demo/README.md
git commit -m "docs: explain standalone product demo"
```
