import { useEffect, useRef, type ReactNode } from 'react'

export default function Dialog({ titleId, wide, onClose, children }: {
  titleId: string; wide?: boolean; onClose: () => void; children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])
  return <dialog ref={ref} className={`product-dialog${wide ? ' wide-dialog' : ''}`} aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); onClose() }}>{children}</dialog>
}
