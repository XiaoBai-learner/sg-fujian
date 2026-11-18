import { useState, type FormEvent } from 'react'
import Icon from '../../shared/Icon'
import { api, type LoginSession } from '../../shared/api/session'

export default function LoginPage({ initialized, onLogin }: { initialized: boolean; onLogin: (session: LoginSession) => void }) {
  const [username, setUsername] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [setup, setSetup] = useState(!initialized)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (setup && password !== confirmation) { setError('两次输入的密码不一致'); return }
    setBusy(true); setError('')
    try {
      const session = await api<LoginSession>(`auth/${setup ? 'setup' : 'login'}`,
        { username, password, ...(setup ? { display_name: name } : {}) })
      setPassword(''); setConfirmation(''); onLogin(session)
    } catch (error) {
      setError(error instanceof Error ? error.message : '登录失败')
      const status = await api<{initialized: boolean}>('auth/status').catch(() => null)
      if (status?.initialized) setSetup(false)
    } finally { setBusy(false) }
  }
  return <main className="login-page">
    <div className="login-brand"><Icon name="trace" size={29} /><strong>溯源</strong><span>字段溯源工作台</span></div>
    <section className="login-card" aria-labelledby="login-title">
      <span className="login-mark"><Icon name="shield" size={28} /></span>
      <h1 id="login-title">{setup ? '创建首个账户' : '登录工作台'}</h1>
      <p>{setup ? '设置你的账户后，开始接入材料与本体建模。' : '使用你的账户访问材料、本体与字段溯源。'}</p>
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <label htmlFor="login-username">账号</label>
          <input id="login-username" autoComplete="username" value={username} required minLength={3} maxLength={64}
            pattern="[A-Za-z0-9_.-]+" onChange={event => setUsername(event.target.value)} autoFocus />
          <small>3–64 位字母、数字、点、下划线或连字符</small>
          {setup && <><label htmlFor="login-name">显示名称</label><input id="login-name" value={name}
            required maxLength={80} autoComplete="name" onChange={event => setName(event.target.value)} /></>}
          <label htmlFor="login-password">密码</label>
          <input id="login-password" type="password" autoComplete={setup ? 'new-password' : 'current-password'}
            value={password} required minLength={setup ? 12 : 1} maxLength={128} onChange={event => setPassword(event.target.value)} />
          {setup && <><small>使用至少 12 位密码</small><label htmlFor="login-confirmation">确认密码</label>
            <input id="login-confirmation" type="password" required value={confirmation} autoComplete="new-password"
              onChange={event => setConfirmation(event.target.value)} /></>}
          {error && <p className="message error" role="alert">{error}</p>}
          <button className="button primary" type="submit">{busy ? '正在验证…' : setup ? '创建账户并进入' : '登录'}<Icon name="arrow" size={17} /></button>
        </fieldset>
      </form>
      <p className="login-help">{setup ? '没有预设账户与默认密码。' : '如需开通账户，请联系现有工作区成员。'}</p>
    </section>
    <p className="login-footer">从原始材料建立本体，让字段来源有据可查。</p>
  </main>
}
