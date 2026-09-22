export default function PanelCard({ title, subtitle, children, actions, id, className = '' }) {
  return (
    <section
      id={id}
      className={`rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-sm transition-all dark:border-slate-800/90 dark:bg-slate-900/90 ${className}`.trim()}
    >
      {(title || actions) && (
        <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 dark:border-slate-800/60 pb-4">
          <div>
            {title && (
              <h2 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 font-display">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                {subtitle}
              </p>
            )}
          </div>
          {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  )
}
