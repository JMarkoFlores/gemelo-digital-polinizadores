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
  Legend,
} from 'recharts'
import { useTranslation } from 'react-i18next'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import PanelCard from './PanelCard'
import MetricCard from './MetricCard'
import EmptyState from './EmptyState'

function ResultLeafletCard({ title, subtitle, mix, geometry, center, optimal }) {
  const { t } = useTranslation()
  const mapStyle = optimal
    ? { fillColor: '#10b981', fillOpacity: 0.55, color: '#f59e0b', weight: 3 }
    : { fillColor: '#64748b', fillOpacity: 0.25, color: '#94a3b8', weight: 2 }

  const cropPct = Number(mix?.crop_area_pct ?? 0)
  const naturalPct = Number(mix?.natural_area_pct ?? 0)
  const floralPct = Number(mix?.floral_strips_pct ?? 0)

  return (
    <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/90 dark:bg-slate-900/90">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-slate-100 font-display text-base">
              {title}
            </h3>
            {subtitle && (
              <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
            )}
          </div>
          {optimal ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Recomendación IA
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              Estado Actual
            </span>
          )}
        </div>

        {/* Satellite Map */}
        <div className="relative z-0 h-60 w-full overflow-hidden rounded-xl border border-slate-200/80 dark:border-slate-800">
          {center && (
            <MapContainer
              center={center}
              zoom={13}
              zoomControl={false}
              dragging={false}
              scrollWheelZoom={false}
              className="h-full w-full"
            >
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles &copy; Esri"
              />
              {geometry && <GeoJSON data={geometry} pathOptions={mapStyle} />}
            </MapContainer>
          )}

          <div className="pointer-events-none absolute bottom-2 right-2 rounded-md bg-black/60 px-2 py-0.5 text-[10px] text-white/90 backdrop-blur-xs font-mono">
            Esri World Imagery
          </div>
        </div>

        {/* Proportional Land-Use Bar */}
        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-xs font-medium text-slate-600 dark:text-slate-300">
            <span>Distribución de Superficie</span>
            <span className="font-mono text-slate-400">100% Total</span>
          </div>
          <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              style={{ width: `${cropPct}%` }}
              className="bg-emerald-500 transition-all"
              title={`Cultivo: ${cropPct.toFixed(1)}%`}
            />
            <div
              style={{ width: `${naturalPct}%` }}
              className="bg-sky-500 transition-all"
              title={`Seminatural: ${naturalPct.toFixed(1)}%`}
            />
            <div
              style={{ width: `${floralPct}%` }}
              className="bg-amber-400 transition-all"
              title={`Franjas: ${floralPct.toFixed(1)}%`}
            />
          </div>
        </div>

        {/* Breakdown Metric Chips */}
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-2.5 dark:bg-emerald-500/[0.08]">
            <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
              {t('results_crop')}
            </p>
            <p className="mt-1 text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {mix?.crop_area_pct?.toFixed?.(1) ?? 'N/A'}%
            </p>
          </div>
          <div className="rounded-xl border border-sky-500/20 bg-sky-500/[0.04] p-2.5 dark:bg-sky-500/[0.08]">
            <p className="text-[10px] font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300">
              {t('results_seminatural')}
            </p>
            <p className="mt-1 text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {mix?.natural_area_pct?.toFixed?.(1) ?? 'N/A'}%
            </p>
          </div>
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-2.5 dark:bg-amber-500/[0.08]">
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
              {t('results_floralStrips')}
            </p>
            <p className="mt-1 text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {mix?.floral_strips_pct?.toFixed?.(1) ?? 'N/A'}%
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

const CustomScatterTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="rounded-xl border border-slate-200 bg-white/95 p-3 shadow-lg backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/95 text-xs">
        <p className="font-bold text-slate-900 dark:text-slate-100 font-display">
          {data.crop_yield_index ? 'Punto de Simulación' : 'Solución'}
        </p>
        <div className="mt-1.5 space-y-1">
          <p className="text-slate-600 dark:text-slate-300">
            Rendimiento:{' '}
            <strong className="text-emerald-600 dark:text-emerald-400">
              {Number(data.crop_yield_index || 0).toFixed(3)}
            </strong>
          </p>
          <p className="text-slate-600 dark:text-slate-300">
            Polinizadores:{' '}
            <strong className="text-sky-600 dark:text-sky-400">
              {Number(data.pollinator_abundance_index || 0).toFixed(3)}
            </strong>
          </p>
        </div>
      </div>
    )
  }
  return null
}

export default function ResultsDashboard({ result }) {
  const { t } = useTranslation()

  if (!result) {
    return (
      <EmptyState
        title={t('results_pending_title')}
        description={t('results_pending_desc')}
        icon={
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>
          </svg>
        }
      />
    )
  }

  const isHypothesisConfirmed =
    result.hypothesis_status?.toLowerCase?.().includes('confirm') ||
    result.hypothesis_status?.toLowerCase?.().includes('validad')

  const deltaYieldSign = result.delta_yield >= 0 ? '+' : ''
  const deltaPollinatorsSign = result.delta_pollinators >= 0 ? '+' : ''

  return (
    <div id="results-dashboard" className="space-y-6">
      {/* Metric Cards Top Row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={t('results_deltaYield')}
          value={`${deltaYieldSign}${result.delta_yield.toFixed(3)}`}
          hint={t('results_deltaYield_hint')}
          tone="emerald"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
            </svg>
          }
        />
        <MetricCard
          label={t('results_deltaPollinators')}
          value={`${deltaPollinatorsSign}${result.delta_pollinators.toFixed(1)}%`}
          hint={t('results_deltaPollinators_hint')}
          tone="emerald"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
              <path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          }
        />
        <MetricCard
          label={t('results_hypothesis')}
          value={
            <span className={`inline-flex items-center gap-1.5 text-base sm:text-lg font-bold px-3 py-1 rounded-full ${
              isHypothesisConfirmed
                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : 'bg-amber-500/10 text-amber-700 dark:text-amber-300'
            }`}>
              <span className={`h-2 w-2 rounded-full ${isHypothesisConfirmed ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              {result.hypothesis_status}
            </span>
          }
          hint={t('results_hypothesis_hint')}
        />
        <MetricCard
          label={t('results_cache')}
          value={
            <span className="text-base sm:text-lg font-bold text-slate-800 dark:text-slate-200">
              {result.cache_hit ? `⚡ ${t('results_cache_hit')}` : `✨ ${t('results_cache_new')}`}
            </span>
          }
          hint={`${t('results_cache')} (${result.model_version || 'v1.0.0-prod'})`}
        />
      </div>

      {/* Spatial Comparison Maps */}
      <PanelCard
        title={t('results_spatial_title')}
        subtitle={t('results_spatial_sub')}
      >
        <div className="grid gap-5 xl:grid-cols-2">
          <ResultLeafletCard
            title={t('results_baseLandscape')}
            subtitle="Configuración inicial del polígono delimitado"
            mix={result.baseline}
            geometry={result.baseline.geometry}
            center={result.baseline.center || [-8.1, -79.0]}
            optimal={false}
          />
          <ResultLeafletCard
            title={t('results_optLandscape')}
            subtitle="Matriz agroecológica optimizada con balance multiobjetivo"
            mix={result.optimized_landscape.land_use_mix}
            geometry={result.baseline.geometry}
            center={result.baseline.center || [-8.1, -79.0]}
            optimal={true}
          />
        </div>
      </PanelCard>

      {/* Pareto Front & Best Solution Breakdown */}
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <PanelCard
          title={t('results_pareto_title')}
          subtitle={t('results_pareto_sub')}
        >
          <div className="h-80 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 15, left: -10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} />
                <XAxis
                  type="number"
                  dataKey="crop_yield_index"
                  name={t('results_yield_axis')}
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  label={{ value: t('results_yield_axis'), position: 'bottom', offset: 0, fontSize: 11, fill: '#64748b' }}
                />
                <YAxis
                  type="number"
                  dataKey="pollinator_abundance_index"
                  name={t('results_pollinators_axis')}
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  label={{ value: t('results_pollinators_axis'), angle: -90, position: 'left', offset: 20, fontSize: 11, fill: '#64748b' }}
                />
                <Tooltip content={<CustomScatterTooltip />} />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />
                <Scatter
                  name="Frente de Soluciones (NSGA-II)"
                  data={result.pareto_front}
                  fill="#38bdf8"
                  fillOpacity={0.5}
                />
                <Scatter
                  name="Línea Base"
                  data={[result.baseline]}
                  fill="#64748b"
                  shape="circle"
                />
                <Scatter
                  name="Solución Óptima Elegida"
                  data={[result.best_solution]}
                  fill="#10b981"
                  shape="star"
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </PanelCard>

        <PanelCard
          title={t('results_best_title')}
          subtitle={t('results_best_sub')}
        >
          <div className="space-y-2 text-xs sm:text-sm">
            {Object.entries(result.best_solution).map(([key, value]) => {
              // Human readable format
              const labels = {
                crop_yield_index: 'Rendimiento proyectado',
                pollinator_abundance_index: 'Abundancia polinizadores',
                crop_area_pct: '% Área de cultivo',
                natural_area_pct: '% Área natural',
                floral_strips_pct: '% Franjas florales',
                pesticide_level: 'Nivel pesticidas',
              }
              const displayLabel = labels[key] || key.replace(/_/g, ' ')

              return (
                <div
                  key={key}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/70 px-3.5 py-2.5 dark:border-slate-800 dark:bg-slate-950/50"
                >
                  <span className="font-medium text-slate-600 dark:text-slate-300 capitalize">
                    {displayLabel}
                  </span>
                  <span className="font-bold text-slate-900 dark:text-slate-100 font-display">
                    {typeof value === 'number' ? value.toFixed(3) : String(value)}
                  </span>
                </div>
              )
            })}
          </div>
        </PanelCard>
      </div>

      {/* Trajectory comparison line chart */}
      <PanelCard
        title={t('results_traj_title')}
        subtitle={t('results_traj_sub')}
      >
        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={[
                {
                  stage: t('results_base'),
                  yield: result.baseline.crop_yield_index,
                  pollinators: result.baseline.pollinator_abundance_index,
                },
                {
                  stage: t('results_optimal'),
                  yield: result.best_solution.crop_yield_index,
                  pollinators: result.best_solution.pollinator_abundance_index,
                },
              ]}
              margin={{ top: 20, right: 20, left: -10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} />
              <XAxis dataKey="stage" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />
              <Line
                name="Rendimiento del Cultivo"
                type="monotone"
                dataKey="yield"
                stroke="#10b981"
                strokeWidth={3}
                dot={{ r: 6, fill: '#10b981' }}
              />
              <Line
                name="Abundancia de Polinizadores"
                type="monotone"
                dataKey="pollinators"
                stroke="#f59e0b"
                strokeWidth={3}
                dot={{ r: 6, fill: '#f59e0b' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </PanelCard>
    </div>
  )
}
