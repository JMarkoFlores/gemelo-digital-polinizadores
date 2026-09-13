export default function StatusBanner({ tone = 'info', children, id }) {
  const styles = {
    info: 'bg-sky-500/10 text-sky-800 dark:text-sky-300 border-sky-500/20',
    error: 'bg-rose-500/10 text-rose-800 dark:text-rose-300 border-rose-500/20',
    success: 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/20',
  }

  const icons = {
    info: (
      <svg className="h-4 w-4 shrink-0 text-sky-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
    ),
    error: (
      <svg className="h-4 w-4 shrink-0 text-rose-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    ),
    success: (
      <svg className="h-4 w-4 shrink-0 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
    ),
    warning: (
      <svg className="h-4 w-4 shrink-0 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    ),
  }

  return (
    <div
      id={id}
      className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-xs sm:text-sm font-medium ${styles[tone] || styles.info}`}
    >
      {icons[tone] || icons.info}
      <div className="flex-1">{children}</div>
    </div>
  )
}
