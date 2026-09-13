export default function SpinnerBlock({ label = 'Cargando' }) {
  return (
    <div className="flex items-center justify-center rounded-2xl border border-slate-200/90 bg-white p-8 dark:border-slate-800/90 dark:bg-slate-900/90 shadow-sm">
      <div className="flex flex-col sm:flex-row items-center gap-3 text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-300">
        <svg className="h-5 w-5 animate-spin text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <span>{label}</span>
      </div>
    </div>
  )
}
