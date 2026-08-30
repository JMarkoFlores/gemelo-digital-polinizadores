export default function AuthCard({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top,_rgba(34,197,94,0.20),_transparent_35%),linear-gradient(135deg,#020617,#0f172a_45%,#14532d)] p-6">
      <div className="w-full max-w-md rounded-[2rem] border border-white/10 bg-slate-950/80 p-8 text-slate-100 shadow-panel backdrop-blur">
        <p className="text-xs uppercase tracking-[0.35em] text-primary-500">Gemelos Digitales</p>
        <h1 className="mt-4 text-3xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-slate-300">{subtitle}</p>
        <div className="mt-8">{children}</div>
        {footer ? <div className="mt-6 text-sm text-slate-400">{footer}</div> : null}
      </div>
    </div>
  )
}
