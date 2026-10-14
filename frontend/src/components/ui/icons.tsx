import type { ReactNode } from 'react'

export type IconName =
  | 'home' | 'practice' | 'flag' | 'chart' | 'user' | 'flask'
  | 'logout' | 'arrow' | 'check' | 'trend' | 'database' | 'formula'
  | 'evaluation' | 'info' | 'alert' | 'clock' | 'plus'

const paths: Record<IconName, ReactNode> = {
  home: <><path d="M4 10.6 12 4l8 6.6" /><path d="M6 9.4V19a1 1 0 0 0 1 1h3v-5h4v5h3a1 1 0 0 0 1-1V9.4" /></>,
  practice: <><path d="M4 20h4L18 10l-4-4L4 16v4Z" /><path d="m13.4 6.6 4 4" /></>,
  flag: <><path d="M6 21V4" /><path d="M6 4h11l-2 3.8 2 3.8H6" /></>,
  chart: <><path d="M4 20h16" /><rect x="6" y="11" width="3" height="6" rx="1" /><rect x="11" y="7" width="3" height="10" rx="1" /><rect x="16" y="13" width="3" height="4" rx="1" /></>,
  user: <><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
  flask: <><path d="M9 3h6" /><path d="M10 3v6L5.2 18a2 2 0 0 0 1.8 3h10a2 2 0 0 0 1.8-3L14 9V3" /><path d="M7.6 14h8.8" /></>,
  logout: <><path d="M15 4h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3" /><path d="M10 12H3" /><path d="m6 9-3 3 3 3" /></>,
  arrow: <><path d="M5 12h13" /><path d="m12.5 6 6 6-6 6" /></>,
  check: <path d="M5 12.5 10 17l9-10" />,
  trend: <><path d="M4 16.5 9 11l4 4 7-8" /><path d="M15 7h5v5" /></>,
  database: <><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6" /><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" /></>,
  formula: <path d="M17 5H7l5 7-5 7h10" />,
  evaluation: <><path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 19v-6" /><path d="M12 19V8" /><path d="M16 19v-3" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  alert: <><path d="M12 4 3 20h18L12 4Z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7.5v5l3 1.8" /></>,
  plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
}

export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return (
    <svg className={`icon ${className}`} viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {paths[name]}
    </svg>
  )
}
