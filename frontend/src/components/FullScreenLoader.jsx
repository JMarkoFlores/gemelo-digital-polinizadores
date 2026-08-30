export default function FullScreenLoader({ label }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/90 px-8 py-6 shadow-panel">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-primary-500" />
          <p className="text-sm font-medium">{label}</p>
        </div>
      </div>
    </div>
  )
}
