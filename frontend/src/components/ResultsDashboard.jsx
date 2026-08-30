import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTranslation } from 'react-i18next'
import PanelCard from './PanelCard'
import MetricCard from './MetricCard'
import EmptyState from './EmptyState'

function ResultMapCard({ title, data }) {
  const { t } = useTranslation()
  const mix = data?.land_use_mix ?? data
  return (
    <div className="rounded-[1.5rem] border border-slate-200 p-4 dark:border-slate-800">
      <p className="text-sm font-medium">{title}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl bg-emerald-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{t('results_crop')}</p>
          <p className="mt-2 text-2xl font-semibold">{mix?.crop_area_pct?.toFixed?.(1) ?? 'N/A'}%</p>
        </div>
        <div className="rounded-2xl bg-sky-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{t('results_seminatural')}</p>
          <p className="mt-2 text-2xl font-semibold">{mix?.natural_area_pct?.toFixed?.(1) ?? 'N/A'}%</p>
        </div>
        <div className="rounded-2xl bg-amber-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{t('results_floralStrips')}</p>
          <p className="mt-2 text-2xl font-semibold">{mix?.floral_strips_pct?.toFixed?.(1) ?? 'N/A'}%</p>
        </div>
      </div>
    </div>
  )
}

export default function ResultsDashboard({ result }) {
  const { t } = useTranslation()

  if (!result) {
    return <EmptyState title={t('results_pending_title')} description={t('results_pending_desc')} />
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label={t('results_deltaYield')} value={result.delta_yield.toFixed(3)} hint={t('results_deltaYield_hint')} />
        <MetricCard label={t('results_deltaPollinators')} value={`${result.delta_pollinators.toFixed(1)}%`} hint={t('results_deltaPollinators_hint')} />
        <MetricCard label={t('results_hypothesis')} value={result.hypothesis_status} hint={t('results_hypothesis_hint')} />
        <MetricCard label={t('results_cache')} value={result.cache_hit ? t('results_cache_hit') : t('results_cache_new')} hint={`${t('results_cache')} ${result.model_version || 'N/A'}`} />
      </div>

      <PanelCard title={t('results_spatial_title')} subtitle={t('results_spatial_sub')}>
        <div className="grid gap-4 xl:grid-cols-2">
          <ResultMapCard title={t('results_baseLandscape')} data={result.baseline} />
          <ResultMapCard title={t('results_optLandscape')} data={result.optimized_landscape} />
        </div>
      </PanelCard>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <PanelCard title={t('results_pareto_title')} subtitle={t('results_pareto_sub')}>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="crop_yield_index" name={t('results_yield_axis')} />
                <YAxis type="number" dataKey="pollinator_abundance_index" name={t('results_pollinators_axis')} />
                <Tooltip cursor={{ strokeDasharray: '4 4' }} />
                <Scatter data={result.pareto_front} fill="#22c55e" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </PanelCard>

        <PanelCard title={t('results_best_title')} subtitle={t('results_best_sub')}>
          <div className="space-y-3 text-sm">
            {Object.entries(result.best_solution).map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3 dark:bg-slate-950/50">
                <span className="text-slate-500 dark:text-slate-400">{key}</span>
                <span className="text-right font-medium">{typeof value === 'number' ? value.toFixed(3) : value}</span>
              </div>
            ))}
          </div>
        </PanelCard>
      </div>

      <PanelCard title={t('results_traj_title')} subtitle={t('results_traj_sub')}>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={[
                { stage: t('results_base'), yield: result.baseline.crop_yield_index, pollinators: result.baseline.pollinator_abundance_index },
                { stage: t('results_optimal'), yield: result.best_solution.crop_yield_index, pollinators: result.best_solution.pollinator_abundance_index },
              ]}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="stage" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="yield" stroke="#0f766e" strokeWidth={3} />
              <Line type="monotone" dataKey="pollinators" stroke="#f59e0b" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </PanelCard>
    </div>
  )
}
