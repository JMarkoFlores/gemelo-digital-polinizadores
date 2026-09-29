import { useEffect, useState } from 'react'

export default function SpinnerBlock({ label = 'Cargando', timeoutSeconds = 10, onTimeoutRetry }) {
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    if (!timeoutSeconds || timeoutSeconds <= 0) return

    const timer = setTimeout(() => {
      setTimedOut(true)
    }, timeoutSeconds * 1000)

    return () => clearTimeout(timer)
  }, [timeoutSeconds])

  if (timedOut) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-amber-500/30 bg-amber-500/5 p-8 text-center dark:border-amber-500/20 dark:bg-amber-950/20 shadow-sm my-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 mb-3">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
          La carga del módulo está tardando más de lo esperado
        </h3>
        <p className="mt-1.5 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md">
          El módulo o sus dependencias aún se están preparando. Puedes esperar unos segundos más o reintentar la carga.
        </p>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => {
              setTimedOut(false)
              if (onTimeoutRetry) {
                onTimeoutRetry()
              } else {
                window.location.reload()
              }
            }}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-500"
          >
            🔄 Reintentar carga
          </button>
        </div>
      </div>
    )
  }

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
