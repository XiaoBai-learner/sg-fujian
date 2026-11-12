import type { ReactNode } from 'react'
import type { Role, Session, UserProfile } from '../domain/types'
import StatusBadge from './StatusBadge'

type NavItem = { path: string; label: string; index: string; group: string; roles: Role[] }
const NAV: NavItem[] = [
  { path: '/workbench', label: '我的工作台', index: '01', group: '字段溯源', roles: ['analyst', 'modeler', 'reviewer', 'admin'] },
  { path: '/requests/new', label: '新建溯源需求', index: '02', group: '字段溯源', roles: ['analyst', 'modeler', 'reviewer', 'admin'] },
  { path: '/knowledge', label: '知识工作台', index: '03', group: '知识工作台', roles: ['modeler', 'reviewer', 'admin'] },
  { path: '/knowledge/materials', label: '资料与结构', index: '04', group: '知识工作台', roles: ['modeler', 'reviewer', 'admin'] },
  { path: '/knowledge/model', label: '语义模型', index: '05', group: '知识工作台', roles: ['modeler', 'reviewer', 'admin'] },
  { path: '/knowledge/validation', label: '验证与试问', index: '06', group: '知识工作台', roles: ['modeler', 'reviewer', 'admin'] },
  { path: '/knowledge/versions', label: '版本与发布', index: '07', group: '知识工作台', roles: ['modeler', 'reviewer', 'admin'] },
  { path: '/admin/connections', label: '系统连接', index: '08', group: '系统管理', roles: ['admin'] },
  { path: '/admin/audit', label: '审计记录', index: '09', group: '系统管理', roles: ['admin', 'reviewer'] },
]

const groups = ['字段溯源', '知识工作台', '系统管理']

export default function AppShell({ session, users, activePath, onNavigate, onRoleChange, children }: {
  session: Session
  users: UserProfile[]
  activePath: string
  onNavigate: (path: string) => void
  onRoleChange: (userId: string) => void
  children: ReactNode
}) {
  const visible = NAV.filter(item => item.roles.includes(session.user.role))
  const active = visible.find(item => activePath === item.path || (item.path !== '/workbench' && activePath.startsWith(item.path)))
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="/workbench" onClick={event => { event.preventDefault(); onNavigate('/workbench') }}>
        <img src="/sgtrace-mark.svg" alt="" />
        <span><strong>字段溯源平台</strong><small>福建电力 · 1.0 产品原型</small></span>
      </a>
      {groups.map(group => {
        const items = visible.filter(item => item.group === group)
        if (!items.length) return null
        return <nav className="nav-group" key={group} aria-label={group}>
          <h2>{group}</h2>
          {items.map(item => <button className={`nav-item${active?.path === item.path ? ' active' : ''}`} key={item.path} type="button" onClick={() => onNavigate(item.path)}>
            <span className="nav-index">{item.index}</span><span>{item.label}</span>
          </button>)}
        </nav>
      })}
      <div className="sidebar-foot">原型状态：mock service<br />查询结果固定知识版本<br />后续替换为真实 API 适配器</div>
    </aside>
    <section className="main-shell">
      <header className="topbar">
        <div className="crumb"><span>福建电力</span><b>/</b><strong>{active?.label || '产品原型'}</strong></div>
        <div className="top-spacer" />
        <span className="env-pill">测试环境</span>
        <span className="version-pill">{session.latestVersionId}</span>
        <select className="role-select" value={session.user.id} aria-label="切换演示角色" onChange={event => onRoleChange(event.target.value)}>
          {users.map(user => <option key={user.id} value={user.id}>{user.name} · {user.title}</option>)}
        </select>
        <div className="user-chip"><span className="user-avatar" aria-hidden="true">{session.user.name.slice(0, 1)}</span><span><b>{session.user.name}</b><small>{session.user.organization}</small></span></div>
      </header>
      <main className="content">{children}</main>
    </section>
  </div>
}
