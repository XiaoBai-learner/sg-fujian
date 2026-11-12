import type { ReactNode } from 'react'

export default function KnowledgeTabs({ active, onChange, children }: { active: string; onChange: (id: string) => void; children?: ReactNode }) {
  const tabs = [['overview', '总览'], ['materials', '资料与结构'], ['model', '语义模型'], ['validation', '验证与试问'], ['versions', '版本与发布']]
  return <><div className="tabs section-gap">{tabs.map(([id, label]) => <button className={`tab${active === id ? ' active' : ''}`} type="button" key={id} onClick={() => onChange(id)}>{label}</button>)}</div>{children}</>
}
