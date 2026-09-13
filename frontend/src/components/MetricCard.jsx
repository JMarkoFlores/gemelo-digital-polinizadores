export default function MetricCard({ label, value, hint, icon, tone = 'default', id }) {
  const toneBorder = {
    default: 'border-slate-200/90 dark:border-slate-800/90',
    emerald: 'border-emerald-500/30 bg-emerald-500/[0.02]',
    amber: 'border-amber-500/30 bg-amber-500/[0.02]',
    blue: 'border-blue-500/30 bg-blue-500/[0.02]',
  }

  return (
    <div
      id={id}
      className={`rounded-2xl border bg-white p-5 shadow-sm transition-all hover:shadow-card dark:bg-slate-900/90 ${toneBorder[tone] || toneBorder.default}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</p>
        {icon && <div className="text-slate-400 dark:text-slate-500">{icon}</div>}
      </div>
      <p className="mt-3 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 font-display">
        {value}
      </p>
      {hint && (
        <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          {hint}
        </p>
      )}
    </div>
  )
}
