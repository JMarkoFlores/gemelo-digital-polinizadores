import { useTranslation } from 'react-i18next'
import EmptyState from './EmptyState'
import PanelCard from './PanelCard'

export default function SimulationHistoryList({ data, loading, page, total, pageSize, onPageChange, onSelect, onExport }) {
  const { t } = useTranslation()
  return (
    <PanelCard title={t('histList_title')} subtitle={t('histList_sub')}>
      {loading ? (
        <div className="grid gap-3">
          {[...Array(3)].map((_, index) => <div key={index} className="h-24 animate-pulse rounded-[1.5rem] bg-slate-100 dark:bg-slate-800" />)}
        </div>
      ) : data.length === 0 ? (
        <EmptyState title={t('histList_empty_title')} description={t('histList_empty_desc')} />
      ) : (
        <div className="space-y-3">
          {data.map((item) => (
            <div key={item.id} className="flex flex-col gap-3 rounded-[1.5rem] border border-slate-200 p-4 dark:border-slate-800 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="font-medium">{t('histList_sim_label', { id: item.id })}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{new Date(item.fecha).toLocaleString()} | {t('histList_user', { id: item.usuario_id })}</p>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  {t('histList_baseYield')}: {item.metricas_base?.crop_yield_index ?? item.metricas_base?.rendimiento ?? 'N/A'} | {t('histList_pollinators')}: {item.metricas_base?.pollinator_abundance_index ?? item.metricas_base?.polinizadores ?? 'N/A'}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => onSelect(item)} className="rounded-2xl bg-slate-200 px-4 py-2 text-sm dark:bg-slate-800">{t('histList_openBtn')}</button>
                <button onClick={() => onExport(item)} className="rounded-2xl bg-primary-600 px-4 py-2 text-sm text-white">PDF</button>
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2 text-sm">
            <span className="text-slate-500 dark:text-slate-400">{t('histList_page', { page, total: Math.max(1, Math.ceil(total / pageSize)) })}</span>
            <div className="flex gap-2">
              <button onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page === 1} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">{t('histList_prev')}</button>
              <button onClick={() => onPageChange(page + 1)} disabled={page * pageSize >= total} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">{t('histList_next')}</button>
            </div>
          </div>
        </div>
      )}
    </PanelCard>
  )
}
