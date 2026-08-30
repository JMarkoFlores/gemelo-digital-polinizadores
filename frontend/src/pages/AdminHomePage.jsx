import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../lib/api'
import MetricCard from '../components/MetricCard'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

export default function AdminHomePage() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/admin/dashboard').then((response) => setData(response.data)).catch((requestError) => setError(requestError.response?.data?.detail || t('adminHome_errorLoad')))
  }, [])

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">{t('adminHome_badge')}</p>
        <h1 className="mt-3 text-4xl font-semibold">{t('adminHome_title')}</h1>
      </section>
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label={t('adminHome_totalUsers')} value={data?.total_users ?? '...'} hint={t('adminHome_totalUsers_hint')} />
        <MetricCard label={t('adminHome_activeUsers')} value={data?.active_users ?? '...'} hint={t('adminHome_activeUsers_hint')} />
        <MetricCard label={t('adminHome_simMonth')} value={data?.simulations_this_month ?? '...'} hint={t('adminHome_simMonth_hint')} />
      </div>
      <PanelCard title={t('adminHome_topZones_title')} subtitle={t('adminHome_topZones_sub')}>
        <div className="grid gap-3 md:grid-cols-2">
          {(data?.top_regions || []).map((region) => (
            <div key={region.region} className="rounded-2xl bg-slate-50 px-4 py-4 dark:bg-slate-950/50">
              <p className="font-medium">{region.region}</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{region.count} {t('adminHome_simulations')}</p>
            </div>
          ))}
        </div>
      </PanelCard>
    </div>
  )
}
