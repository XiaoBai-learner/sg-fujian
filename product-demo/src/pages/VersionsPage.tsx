import { useEffect, useState } from 'react'
import { AsyncState } from '../components/AsyncState'
import StatusBadge from '../components/StatusBadge'
import VersionDiffView from '../components/VersionDiff'
import { approveVersion, getVersionDiff, listKnowledgeVersions, publishVersion } from '../services/mockService'
import type { KnowledgeVersion, VersionDiff } from '../domain/types'

const statusMeta: Record<KnowledgeVersion['status'], { label: string; tone: 'green' | 'amber' | 'red' | 'blue' }> = {
  draft: { label: '草稿', tone: 'blue' }, building: { label: '构建中', tone: 'amber' }, review: { label: '待审核', tone: 'amber' }, published: { label: '已发布', tone: 'green' }, superseded: { label: '历史版本', tone: 'blue' }, rejected: { label: '已退回', tone: 'red' },
}

export default function VersionsPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [versions, setVersions] = useState<KnowledgeVersion[]>([])
  const [selected, setSelected] = useState<KnowledgeVersion>()
  const [diff, setDiff] = useState<VersionDiff>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')
  const load = () => { setLoading(true); listKnowledgeVersions().then(items => { setVersions(items); setSelected(items.find(item => item.status === 'review') || items[0]); return items.find(item => item.status === 'review') }).then(item => item && getVersionDiff(item.id).then(setDiff)).catch(e => setError(e instanceof Error ? e.message : '版本读取失败')).finally(() => setLoading(false)) }
  useEffect(load, [])
  const select = (version: KnowledgeVersion) => { setSelected(version); getVersionDiff(version.id).then(setDiff) }
  const approve = async () => { if (!selected) return; setBusy(true); try { const next = await approveVersion(selected.id); setSelected(next); setVersions(await listKnowledgeVersions()); setToast('审核已通过，现在可以发布候选版本。') } catch (e) { setError(e instanceof Error ? e.message : '审核失败') } finally { setBusy(false) } }
  const publish = async () => { if (!selected) return; setBusy(true); try { await publishVersion(selected.id); setVersions(await listKnowledgeVersions()); setToast(`已发布 ${selected.id}，业务查询会在新任务中使用该版本。`) } catch (e) { setError(e instanceof Error ? e.message : '发布失败') } finally { setBusy(false) } }
  return <AsyncState loading={loading} error={error} onRetry={load}>{selected && <><div className="page-head"><div><p className="page-kicker">KNOWLEDGE WORKSPACE / RELEASES</p><h1>版本与发布</h1><p>候选版本必须通过验证和审核；发布只切换线上版本指针，不重写历史执行。</p></div><div className="page-actions"><button className="btn" type="button" onClick={() => onNavigate('/knowledge/validation')}>查看验证</button>{selected.status === 'review' && <button className="btn" type="button" disabled={busy} onClick={approve}>{busy ? '处理中…' : '审核通过'}</button>}{selected.status === 'review' && selected.reviewNote === '审核通过，等待发布。' && <button className="btn primary" type="button" disabled={busy} onClick={publish}>{busy ? '发布中…' : '发布候选版本'}</button>}</div></div>
    {toast && <div className="notice ok section-gap"><span>{toast}</span></div>}
    <div className="split section-gap"><section className="panel"><div className="panel-head"><div><h2>知识版本</h2><p>版本包不可变；草稿变化会生成新的候选包。</p></div></div><div className="panel-body grid">{versions.map(version => { const meta = statusMeta[version.status]; return <button className={`notice${selected.id === version.id ? ' selected' : ''}`} type="button" key={version.id} onClick={() => select(version)}><StatusBadge label={meta.label} tone={meta.tone} /><span><strong>{version.id} · {version.label}</strong><br />{version.summary.concepts} 对象 · {version.summary.attributes} 属性 · {version.summary.coverage}% 覆盖<br /><small className="muted-cell">{version.createdAt} · {version.createdBy}</small></span><span className="top-spacer">→</span></button> })}</div></section><section className="panel"><div className="panel-head"><div><h2>{selected.id} 版本信息</h2><p>审核人需要同时查看差异、影响字段和验证结论。</p></div><StatusBadge label={statusMeta[selected.status].label} tone={statusMeta[selected.status].tone} /></div><div className="panel-body"><dl className="detail-kv"><dt>输入快照</dt><dd><code>{selected.sourceSnapshot}</code></dd><dt>影响字段</dt><dd>{selected.affectedFields.length ? selected.affectedFields.join('、') : '没有记录'}</dd><dt>审核说明</dt><dd>{selected.reviewNote || '尚未填写'}</dd><dt>当前操作</dt><dd>{selected.status === 'review' ? '查看差异后审核；通过后才能发布。' : selected.status === 'published' ? '线上版本；新查询会固定使用。' : '历史或已退回版本。'}</dd></dl></div></section></div>
    {diff && <section className="panel section-gap"><div className="panel-head"><div><h2>与上一发布版的差异</h2><p>差异是审核记录的一部分，发布后仍可追溯。</p></div></div><div className="panel-body"><VersionDiffView diff={diff} /></div></section>}
  </>}</AsyncState>
}
