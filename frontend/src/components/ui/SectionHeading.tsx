import type { ReactNode } from 'react'

export function SectionHeading({ kicker, title, action }: { kicker?: string; title: ReactNode; action?: ReactNode }) {
  return (
    <div className="section-heading">
      <div className="section-heading-copy">
        {kicker && <div className="card-kicker">{kicker}</div>}
        <h3>{title}</h3>
      </div>
      {action && <div className="section-heading-action">{action}</div>}
    </div>
  )
}
