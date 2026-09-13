export default function AuthCard({ title, subtitle, children, footer }) {
  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 sm:p-6 bg-slate-950 text-slate-100 overflow-hidden">
      {/* Subtle organic ambient aura */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(5,150,105,0.22),transparent_70%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,rgba(6,78,59,0.15),transparent_50%)]" />

      <div className="relative w-full max-w-md rounded-3xl border border-slate-800/90 bg-slate-900/90 p-6 sm:p-8 shadow-panel backdrop-blur-xl transition-all">
        {/* Brand Icon Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a9 9 0 0 1 9 9c0 5-4 9-9 9s-9-4-9-9a9 9 0 0 1 9-9Z" />
              <path d="M12 7v5l3 3" />
              <path d="M7 14c1.5 1 3 1.5 5 1.5s3.5-.5 5-1.5" />
            </svg>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.25em] text-emerald-400">Gemelos Digitales</p>
            <p className="text-xs text-slate-400">Bioeconomía & Polinizadores</p>
          </div>
        </div>

        <div className="mt-6">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white font-display">{title}</h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">{subtitle}</p>
        </div>

        <div className="mt-6">{children}</div>

        {footer ? (
          <div className="mt-6 pt-5 border-t border-slate-800/70 text-center text-sm text-slate-400">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
