import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import MetricCard from '../components/MetricCard'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

export default function AdminHomePage() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/admin/dashboard')
      .then((response) => setData(response.data))
      .catch((requestError) => setError(requestError.response?.data?.detail || t('adminHome_errorLoad')))
  }, [])

  const topRegions = data?.top_regions || []
  const maxRegionCount = Math.max(...topRegions.map((r) => r.count), 1)

  return (
    <div className="space-y-6 sm:space-y-8">
      <section className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('adminHome_badge')}
          </span>
          <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-display">
            {t('adminHome_title')}
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Resumen global de actividad, usuarios y densidad de parcelas simuladas.
          </p>
        </div>

        <div className="flex gap-2">
          <Link
            to="/admin/simulaciones"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          >
            Ver Simulaciones →
          </Link>
          <Link
            to="/admin/usuarios"
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-500"
          >
            Gestionar Usuarios
          </Link>
        </div>
      </section>

      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          label={t('adminHome_totalUsers')}
          value={data?.total_users ?? '...'}
          hint={t('adminHome_totalUsers_hint')}
          tone="emerald"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          }
        />
        <MetricCard
          label={t('adminHome_activeUsers')}
          value={data?.active_users ?? '...'}
          hint={t('adminHome_activeUsers_hint')}
          tone="blue"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-500">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
          }
        />
        <MetricCard
          label={t('adminHome_simMonth')}
          value={data?.simulations_this_month ?? '...'}
          hint={t('adminHome_simMonth_hint')}
          tone="amber"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
              <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>
            </svg>
          }
        />
      </div>

      <PanelCard
        title={t('adminHome_topZones_title')}
        subtitle={t('adminHome_topZones_sub')}
      >
        <div className="grid gap-3 md:grid-cols-2">
          {topRegions.map((region) => {
            const pct = Math.round((region.count / maxRegionCount) * 100)
            return (
              <div
                key={region.region}
                className="rounded-2xl border border-slate-200/90 bg-white p-4.5 shadow-xs transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 dark:text-slate-100 font-display text-sm">
                    {region.region}
                  </span>
                  <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs font-bold text-emerald-700 dark:text-emerald-300">
                    {region.count} {t('adminHome_simulations')}
                  </span>
                </div>

                <div className="mt-3">
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      style={{ width: `${pct}%` }}
                      className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </PanelCard>
    </div>
  )
}
