import { useTranslation } from 'react-i18next'
import EmptyState from './EmptyState'
import PanelCard from './PanelCard'

export default function SimulationHistoryList({ data, loading, page, total, pageSize, onPageChange, onSelect, onExport }) {
  const { t } = useTranslation()
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <PanelCard
      id="simulation-history-list"
      title={t('histList_title')}
      subtitle={t('histList_sub')}
      actions={
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
          {total} registro{total === 1 ? '' : 's'} en total
        </span>
      }
    >
      {loading ? (
        <div className="grid gap-3">
          {[...Array(3)].map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/60" />
          ))}
        </div>
      ) : data.length === 0 ? (
        <EmptyState
          title={t('histList_empty_title')}
          description={t('histList_empty_desc')}
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          }
        />
      ) : (
        <div className="space-y-3">
          {data.map((item) => {
            const yieldVal = item.metricas_base?.crop_yield_index ?? item.metricas_base?.rendimiento
            const pollVal = item.metricas_base?.pollinator_abundance_index ?? item.metricas_base?.polinizadores

            return (
              <div
                key={item.id}
                className="flex flex-col gap-4 rounded-2xl border border-slate-200/90 bg-white p-4.5 sm:p-5 shadow-xs transition hover:border-emerald-500/40 hover:shadow-card dark:border-slate-800 dark:bg-slate-900 lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-slate-900 dark:text-slate-100 font-display text-base">
                      {t('histList_sim_label', { id: item.id })}
                    </span>
                    <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                      ID: #{item.id}
                    </span>
                    <span className="text-xs text-slate-400">
                      {new Date(item.fecha.endsWith('Z') ? item.fecha : item.fecha + 'Z').toLocaleString()}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-300 pt-1">
                    <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1 dark:bg-slate-800/60">
                      <span className="text-slate-400">{t('histList_baseYield')}:</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200 font-display">
                        {typeof yieldVal === 'number' ? yieldVal.toFixed(3) : yieldVal || 'N/A'}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1 dark:bg-slate-800/60">
                      <span className="text-slate-400">{t('histList_pollinators')}:</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200 font-display">
                        {typeof pollVal === 'number' ? pollVal.toFixed(3) : pollVal || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => onSelect(item)}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>
                    </svg>
                    <span>{t('histList_openBtn')}</span>
                  </button>

                  <button
                    onClick={() => onExport(item, 'pdf')}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-500"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    <span>PDF</span>
                  </button>
                  <button
                    onClick={() => onExport(item, 'word')}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-blue-500"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                    </svg>
                    <span>Word</span>
                  </button>
                  <button
                    onClick={() => onExport(item, 'excel')}
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
            <span>{t('histList_page', { page, total: totalPages })}</span>
            <div className="flex gap-2">
              <button
                onClick={() => onPageChange(Math.max(1, page - 1))}
                disabled={page === 1}
                className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
              >
                {t('histList_prev')}
              </button>
              <button
                onClick={() => onPageChange(page + 1)}
                disabled={page >= totalPages}
                className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
              >
                {t('histList_next')}
              </button>
            </div>
          </div>
        </div>
      )}
    </PanelCard>
  )
}
