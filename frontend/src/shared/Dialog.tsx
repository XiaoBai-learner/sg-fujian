import { useEffect, useRef, type ReactNode } from 'react'
import Icon from './Icon'

export default function Dialog({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { ref.current?.showModal(); return () => ref.current?.close() }, [])
  return <dialog ref={ref} className={`workbench-dialog ${wide ? 'wide-dialog' : ''}`} aria-label={title} onCancel={event => { event.preventDefault(); onClose() }}>
    <div className="dialog-heading"><h2>{title}</h2><button className="icon-button" aria-label={`关闭${title}`} onClick={onClose}><Icon name="close" size={18} /></button></div>
    <div className="dialog-body">{children}</div>
  </dialog>
}
