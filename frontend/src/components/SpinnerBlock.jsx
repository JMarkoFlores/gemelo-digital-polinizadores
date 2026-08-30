export default function SpinnerBlock({ label = 'Cargando' }) {
  return (
    <div className="flex items-center justify-center rounded-[1.5rem] border border-slate-200 bg-white px-4 py-10 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-300">
        <span className="h-3 w-3 animate-pulse rounded-full bg-primary-500" />
        {label}
      </div>
    </div>
  )
}
