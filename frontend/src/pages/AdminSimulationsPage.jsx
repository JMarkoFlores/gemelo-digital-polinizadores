import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../lib/api'
import EmptyState from '../components/EmptyState'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

export default function AdminSimulationsPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({ user_id: '', region: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const pageSize = 8

  const load = () => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (filters.user_id) params.append('user_id', filters.user_id)
    if (filters.region) params.append('region', filters.region)
    api
      .get(`/api/admin/simulations?${params.toString()}`)
      .then((response) => {
        setItems(response.data.items)
        setTotal(response.data.total)
      })
      .catch((requestError) => setError(requestError.response?.data?.detail || t('adminSim_errorLoad')))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [page])

  const exportWord = async (simulationId) => {
    const response = await api.get(`/api/admin/simulations/${simulationId}/report`)
    const { exportSimulationToDocx } = await import('../lib/exporters')
    await exportSimulationToDocx(response.data.simulation)
  }

  const exportExcel = async (simulationId) => {
    const response = await api.get(`/api/admin/simulations/${simulationId}/report`)
    const { exportSimulationToExcel } = await import('../lib/exporters')
    exportSimulationToExcel(response.data.simulation)
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="space-y-6 sm:space-y-8">
      <section>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          {t('adminHome_badge')}
        </span>
        <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-display">
          {t('adminSim_title')}
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Supervisión global de simulaciones agronómicas ejecutadas por todos los usuarios.
        </p>
      </section>

      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      {/* Filters Card */}
      <PanelCard title={t('adminSim_filters_title')} subtitle={t('adminSim_filters_sub')}>
        <div className="grid gap-3 sm:grid-cols-[0.4fr_0.6fr_auto]">
          <div className="relative">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
              <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            <input
              value={filters.user_id}
              onChange={(e) => setFilters((prev) => ({ ...prev, user_id: e.target.value }))}
              placeholder={t('adminSim_filterUserId')}
              className="w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 py-2 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>

          <div className="relative">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>
            </svg>
            <input
              value={filters.region}
              onChange={(e) => setFilters((prev) => ({ ...prev, region: e.target.value }))}
              placeholder={t('adminSim_filterRegion')}
              className="w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 py-2 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>

          <button
            onClick={() => { setPage(1); load() }}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-500"
          >
            {t('adminSim_applyBtn')}
          </button>
        </div>
      </PanelCard>

      {/* List Card */}
      <PanelCard
        title={t('adminSim_list_title')}
        subtitle={t('adminSim_list_sub')}
        actions={
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
            {total} registros
          </span>
        }
      >
        {loading ? (
          <div className="grid gap-3">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="h-28 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/60" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title={t('adminSim_empty_title')}
            description={t('adminSim_empty_desc')}
          />
        ) : (
          <div className="space-y-3">
            {items.map((item) => {
              const yieldVal = item.metricas_optimas?.crop_yield_index ?? item.metricas_optimas?.rendimiento
              const pollVal = item.metricas_optimas?.pollinator_abundance_index ?? item.metricas_optimas?.polinizadores

              return (
                <div
                  key={item.id}
                  className="flex flex-col gap-4 rounded-2xl border border-slate-200/90 bg-white p-4.5 sm:p-5 shadow-xs transition hover:border-emerald-500/40 hover:shadow-card dark:border-slate-800 dark:bg-slate-900 xl:flex-row xl:items-center xl:justify-between"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-slate-900 dark:text-slate-100 font-display text-base">
                        {t('adminSim_item_label', { id: item.id })}
                      </span>
                      <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                        {t('adminSim_item_user', { id: item.usuario_id })}
                      </span>
                      <span className="text-xs text-slate-400">
                        {new Date(item.fecha.endsWith('Z') ? item.fecha : item.fecha + 'Z').toLocaleString()}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-300 pt-1">
                      <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1 dark:bg-slate-800/60">
                        <span className="text-slate-400">{t('adminSim_item_region')}:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200 font-display">
                          {item.metricas_base?.region_label || 'Zona Agrícola'}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1 dark:bg-slate-800/60">
                        <span className="text-slate-400">{t('adminSim_item_yield')}:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200 font-display">
                          {typeof yieldVal === 'number' ? yieldVal.toFixed(3) : yieldVal || 'N/A'}
                        </span>
                      </div>

                      {pollVal !== undefined && (
                        <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1 dark:bg-slate-800/60">
                          <span className="text-slate-400">Polinizadores:</span>
                          <span className="font-bold text-slate-800 dark:text-slate-200 font-display">
                            {typeof pollVal === 'number' ? pollVal.toFixed(3) : pollVal}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={async () => {
                        const { exportSimulationToPdf } = await import('../lib/exporters')
                        exportSimulationToPdf(item)
                      }}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-500">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/>
                      </svg>
                      <span>PDF</span>
                    </button>

                    <button
                      onClick={() => exportWord(item.id)}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-blue-500"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/>
                      </svg>
                      <span>Word</span>
                    </button>

                    <button
                      onClick={() => exportExcel(item.id)}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-green-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-green-500"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>
                      </svg>
                      <span>Excel</span>
                    </button>
                  </div>
                </div>
              )
            })}

            {/* Pagination */}
            <div className="flex items-center justify-between pt-4 text-xs font-medium text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800">
              <span>{t('adminSim_records', { count: total })}</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                  disabled={page === 1}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
                >
                  {t('adminSim_prev')}
                </button>
                <button
                  onClick={() => setPage((value) => value + 1)}
                  disabled={page >= totalPages}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
                >
                  {t('adminSim_next')}
                </button>
              </div>
            </div>
          </div>
        )}
      </PanelCard>
    </div>
  )
}
