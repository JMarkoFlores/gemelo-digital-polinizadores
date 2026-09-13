import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../lib/api'
import PanelCard from '../components/PanelCard'
import SimulationHistoryList from '../components/SimulationHistoryList'
import StatusBanner from '../components/StatusBanner'

export default function ClientHistoryPage() {
  const { t } = useTranslation()
  const [history, setHistory] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showJson, setShowJson] = useState(false)
  const pageSize = 5

  useEffect(() => {
    let active = true
    setLoading(true)
    api
      .get(`/api/simulations/me?page=${page}&page_size=${pageSize}`)
      .then((response) => {
        if (!active) return
        setHistory(response.data.items)
        setTotal(response.data.total)
        setSelected((current) => current ?? response.data.items[0] ?? null)
      })
      .catch((requestError) => {
        if (!active) return
        setError(requestError.response?.data?.detail || t('clientHist_errorLoad'))
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [page])

  return (
    <div className="space-y-6 sm:space-y-8">
      <section>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          {t('clientHist_badge')}
        </span>
        <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-display">
          {t('clientHist_title')}
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Consulta y descarga los informes generados de tus parcelas y simulaciones pasadas.
        </p>
      </section>

      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      <SimulationHistoryList
        data={history}
        loading={loading}
        page={page}
        total={total}
        pageSize={pageSize}
        onPageChange={setPage}
        onSelect={setSelected}
        onExport={async (item, format) => {
          const { exportSimulationToPdf, exportSimulationToDocx, exportSimulationToExcel } = await import('../lib/exporters')
          if (format === 'word') {
            exportSimulationToDocx(item)
          } else if (format === 'excel') {
            exportSimulationToExcel(item)
          } else {
            exportSimulationToPdf(item)
          }
        }}
      />

      {selected ? (
        <PanelCard
          title={t('clientHist_detail_title', { id: selected.id })}
          subtitle={t('clientHist_detail_sub')}
          actions={
            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  const { exportSimulationToPdf } = await import('../lib/exporters')
                  exportSimulationToPdf(selected)
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-500"
                title="Descargar PDF"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span className="hidden sm:inline">PDF</span>
              </button>
              <button
                onClick={async () => {
                  const { exportSimulationToDocx } = await import('../lib/exporters')
                  exportSimulationToDocx(selected)
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-blue-500"
                title="Descargar Word"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                </svg>
                <span className="hidden sm:inline">Word</span>
              </button>
              <button
                onClick={async () => {
                  const { exportSimulationToExcel } = await import('../lib/exporters')
                  exportSimulationToExcel(selected)
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-green-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-green-500"
                title="Descargar Excel"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>
                </svg>
                <span className="hidden sm:inline">Excel</span>
              </button>
              <button
                onClick={() => setShowJson(!showJson)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-xs dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
              >
                {showJson ? 'Ver Resumen' : 'Ver JSON'}
              </button>
            </div>
          }
        >
          {showJson ? (
            <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950 p-4 text-xs font-mono text-emerald-300 border border-slate-800">
              {JSON.stringify(selected, null, 2)}
            </pre>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-950/60">
                  <span className="text-xs text-slate-400">Fecha de Ejecución</span>
                  <p className="mt-1 font-bold text-slate-800 dark:text-slate-200 font-display text-sm">
                    {new Date(selected.fecha.endsWith('Z') ? selected.fecha : selected.fecha + 'Z').toLocaleString()}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-950/60">
                  <span className="text-xs text-slate-400">Rendimiento Base</span>
                  <p className="mt-1 font-bold text-slate-800 dark:text-slate-200 font-display text-sm">
                    {selected.metricas_base?.crop_yield_index?.toFixed?.(3) ?? selected.metricas_base?.rendimiento ?? 'N/A'}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-950/60">
                  <span className="text-xs text-slate-400">Abundancia Polinizadores</span>
                  <p className="mt-1 font-bold text-slate-800 dark:text-slate-200 font-display text-sm">
                    {selected.metricas_base?.pollinator_abundance_index?.toFixed?.(3) ?? selected.metricas_base?.polinizadores ?? 'N/A'}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-950/60">
                  <span className="text-xs text-slate-400">Usuario Asignado</span>
                  <p className="mt-1 font-bold text-slate-800 dark:text-slate-200 font-display text-sm">
                    ID #{selected.usuario_id}
                  </p>
                </div>
              </div>

              {selected.metricas_optimas && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] p-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
                    Métricas de Optimización Alcanzadas
                  </span>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3 text-xs">
                    {Object.entries(selected.metricas_optimas).map(([k, v]) => (
                      <div key={k} className="flex justify-between rounded-lg bg-white/80 p-2 dark:bg-slate-900/80">
                        <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200 font-display">
                          {typeof v === 'number' ? v.toFixed(3) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </PanelCard>
      ) : null}
    </div>
  )
}
