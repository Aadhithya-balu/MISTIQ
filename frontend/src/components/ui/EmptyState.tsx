import type { ReactNode } from 'react'

export function EmptyState({ title, description, children }: { title: string; description: string; children?: ReactNode }) {
  return <div className="state empty-state"><h2>{title}</h2><p>{description}</p>{children && <div className="state-actions">{children}</div>}</div>
}
