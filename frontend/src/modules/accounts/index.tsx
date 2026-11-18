import { useEffect, useState, type FormEvent } from 'react'
import { api, type Account } from '../../shared/api/session'
import Icon from '../../shared/Icon'

export default function AccountsPage({ user, onLogout }: { user: Account; onLogout: () => void }) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [creating, setCreating] = useState(false)
  const [username, setUsername] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const reload = async () => { const value = await api<{ items: Account[] }>('accounts'); setAccounts(value.items) }
  useEffect(() => { void reload().catch(() => setError('账户列表读取失败')) }, [])
  const run = async (work: () => Promise<void>) => {
    if (busy) return
    setBusy(true); setError(''); setNotice('')
    try { await work() } catch (error) { setError(error instanceof Error ? error.message : '操作失败') }
    finally { setBusy(false) }
  }
  const create = (event: FormEvent) => {
    event.preventDefault()
    void run(async () => {
      await api('accounts', { username, display_name: name, password })
      setPassword(''); setName(''); setUsername(''); setCreating(false); await reload(); setNotice('账户已创建')
    })
  }
  const changePassword = (event: FormEvent) => {
    event.preventDefault()
    if (newPassword !== confirmation) { setError('两次输入的新密码不一致'); return }
    void run(async () => {
      await api('auth/password', { current_password: currentPassword, new_password: newPassword })
      setCurrentPassword(''); setNewPassword(''); setConfirmation(''); onLogout()
    })
  }
  return <section className="accounts-page">
    <div className="page-heading"><div><span className="eyebrow">工作区设置</span><h1>账户管理</h1>
      <p>工作区成员共享材料、本体与溯源功能。</p></div><button className="button primary" disabled={busy}
        onClick={() => setCreating(value => !value)}><Icon name="plus" size={17} />新增账户</button></div>
    {error && <p className="message error" role="alert">{error}</p>}
    {notice && <p className="message info" role="status">{notice}</p>}
    {creating && <form className="account-form" onSubmit={create}><h2>新增账户</h2><fieldset disabled={busy}>
      <label>账号<input value={username} onChange={event => setUsername(event.target.value)} required minLength={3}
        maxLength={64} pattern="[A-Za-z0-9_.-]+" autoComplete="off" /></label>
      <label>显示名称<input value={name} onChange={event => setName(event.target.value)} required maxLength={80} /></label>
      <label>初始密码<input type="password" value={password} onChange={event => setPassword(event.target.value)}
        required minLength={12} maxLength={128} autoComplete="new-password" /></label><small>至少 12 位；新成员可登录后修改自己的密码。</small>
      <div className="footer-actions"><button className="button primary" type="submit">创建账户</button>
        <button className="button secondary" type="button" onClick={() => { setCreating(false); setPassword('') }}>取消</button></div>
    </fieldset></form>}
    <div className="account-list table-scroll"><table><thead><tr><th>账号</th><th>显示名称</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>{accounts.map(account => <tr key={account.id}><td>{account.username}{account.id === user.id && <small>当前账户</small>}</td>
        <td>{account.display_name}</td><td><span className={`badge ${account.active ? 'mint' : ''}`}>{account.active ? '正常' : '已停用'}</span></td>
        <td><div className="footer-actions"><button className="text-button" disabled={busy} onClick={() => {
          const displayName = window.prompt('显示名称', account.display_name)
          if (displayName?.trim()) void run(async () => { await api(`accounts/${account.id}`, { display_name: displayName }, 'PATCH'); await reload(); setNotice('名称已更新') })
        }}>修改名称</button><button className="text-button" disabled={busy || account.id === user.id}
          onClick={() => void run(async () => {
            await api(`accounts/${account.id}`, { active: !account.active }, 'PATCH'); await reload()
            setNotice(account.active ? '账户已停用，其登录会话已失效' : '账户已启用')
          })}>{account.active ? '停用' : '启用'}</button></div></td></tr>)}</tbody></table></div>
    <form className="account-form password-form" onSubmit={changePassword}><h2>修改我的密码</h2><p>修改后所有设备需要重新登录。</p>
      <fieldset disabled={busy}><label>当前密码<input type="password" autoComplete="current-password" value={currentPassword}
        onChange={event => setCurrentPassword(event.target.value)} required maxLength={128} /></label>
        <label>新密码<input type="password" autoComplete="new-password" value={newPassword}
          onChange={event => setNewPassword(event.target.value)} required minLength={12} maxLength={128} /></label>
        <label>确认新密码<input type="password" autoComplete="new-password" value={confirmation}
          onChange={event => setConfirmation(event.target.value)} required maxLength={128} /></label>
        <button className="button primary" type="submit">修改密码并重新登录</button></fieldset></form>
  </section>
}
