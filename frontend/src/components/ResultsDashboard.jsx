import { useState } from 'react'
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
import PanelCard from './PanelCard'
import MetricCard from './MetricCard'
import EmptyState from './EmptyState'
import LandscapeDiorama3D from './LandscapeDiorama3D'
import ExpandableMapCard from './ExpandableMapCard'
import RecommendationAccordion from './RecommendationAccordion'


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
  const [spatialViewMode, setSpatialViewMode] = useState('both') // 'satellite' | 'diorama' | 'both'

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
  const deltaPollinatorsVal = Number(result.delta_pollinators ?? 0)

  // Dynamic interpretation for Hypothesis (threshold >= 20%)
  const hypothesisThreshold = 20.0
  const isHypothesisThresholdMet = deltaPollinatorsVal >= hypothesisThreshold
  const hypothesisExplanation = isHypothesisThresholdMet
    ? `La hipótesis planteaba un aumento de al menos 20% en abundancia de polinizadores. El resultado obtenido (+${deltaPollinatorsVal.toFixed(1)}%) confirma la hipótesis.`
    : `La hipótesis planteaba un aumento de al menos 20% en abundancia de polinizadores. El resultado obtenido (${deltaPollinatorsSign}${deltaPollinatorsVal.toFixed(1)}%) no cumplió la hipótesis (faltó un ${(hypothesisThreshold - deltaPollinatorsVal).toFixed(1)}% para alcanzar el umbral).`

  const baselineMix = result.baseline
  const optimalMix = result.optimized_landscape?.land_use_mix || result.best_solution

  return (
    <div id="results-dashboard" className="space-y-6">
      {/* Metric Cards Top Row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          id="metric-delta-yield"
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
          id="metric-delta-pollinators"
          label={t('results_deltaPollinators')}
          value={`${deltaPollinatorsSign}${deltaPollinatorsVal.toFixed(1)}%`}
          hint={t('results_deltaPollinators_hint')}
          tone="emerald"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
              <path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          }
        />
        <MetricCard
          id="metric-hypothesis"
          label={t('results_hypothesis')}
          value={
            <div>
              <span className={`inline-flex items-center gap-1.5 text-base sm:text-lg font-bold px-3 py-1 rounded-full ${
                isHypothesisConfirmed
                  ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                  : 'bg-amber-500/10 text-amber-700 dark:text-amber-300'
              }`}>
                <span className={`h-2 w-2 rounded-full ${isHypothesisConfirmed ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                {result.hypothesis_status}
              </span>
              <p className="mt-2 text-xs font-normal text-slate-600 dark:text-slate-300 leading-relaxed border-t border-slate-100 dark:border-slate-800/80 pt-2">
                {hypothesisExplanation}
              </p>
            </div>
          }
          hint={t('results_hypothesis_hint')}
        />
        <MetricCard
          id="metric-cache"
          label={t('results_cache')}
          value={
            <span className="text-base sm:text-lg font-bold text-slate-800 dark:text-slate-200">
              {result.cache_hit ? `⚡ ${t('results_cache_hit')}` : `✨ ${t('results_cache_new')}`}
            </span>
          }
          hint={`${t('results_cache')} (${result.model_version || 'v1.0.0-prod'})`}
        />
      </div>

      {/* Spatial Comparison: 2D Satellite & 3D Interactive Diorama */}
      <PanelCard
        id="panel-spatial-comparison"
        title={t('results_spatial_title')}
        subtitle={t('results_spatial_sub')}
        actions={
          <div className="flex items-center gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800/80">
            <button
              id="btn-view-satellite"
              type="button"
              onClick={() => setSpatialViewMode('satellite')}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-all ${
                spatialViewMode === 'satellite'
                  ? 'bg-white font-semibold text-slate-900 shadow-xs dark:bg-slate-900 dark:text-slate-100'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              🗺️ Satélite 2D
            </button>
            <button
              id="btn-view-diorama"
              type="button"
              onClick={() => setSpatialViewMode('diorama')}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-all ${
                spatialViewMode === 'diorama'
                  ? 'bg-white font-semibold text-emerald-600 shadow-xs dark:bg-slate-900 dark:text-emerald-400'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              🧊 Maqueta 3D
            </button>
            <button
              id="btn-view-both"
              type="button"
              onClick={() => setSpatialViewMode('both')}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-all ${
                spatialViewMode === 'both'
                  ? 'bg-white font-semibold text-slate-900 shadow-xs dark:bg-slate-900 dark:text-slate-100'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              🔄 Ambas
            </button>
          </div>
        }
      >
        <div className="space-y-6">
          {/* 2D Satellite View */}
          {(spatialViewMode === 'satellite' || spatialViewMode === 'both') && (
            <div>
              {spatialViewMode === 'both' && (
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    🗺️ Vista Satelital 2D (Leaflet)
                  </span>
                </div>
              )}
              <div className="grid gap-5 xl:grid-cols-2">
                <ExpandableMapCard
                  title={t('results_baseLandscape')}
                  subtitle="Configuración inicial del polígono delimitado"
                  mix={result.baseline}
                  geometry={result.baseline.geometry}
                  center={result.baseline.center || [-8.1, -79.0]}
                  optimal={false}
                />
                <ExpandableMapCard
                  title={t('results_optLandscape')}
                  subtitle="Matriz agroecológica optimizada con balance multiobjetivo"
                  mix={result.optimized_landscape.land_use_mix}
                  geometry={result.baseline.geometry}
                  center={result.baseline.center || [-8.1, -79.0]}
                  optimal={true}
                />
              </div>
            </div>
          )}

          {/* 3D Interactive Diorama View */}
          {(spatialViewMode === 'diorama' || spatialViewMode === 'both') && (
            <div>
              {spatialViewMode === 'both' && (
                <div className="mb-3 flex items-center gap-2 border-t border-slate-100 dark:border-slate-800/80 pt-5">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                    🧊 Maqueta 3D Interactiva (Diorama de Uso de Suelo)
                  </span>
                </div>
              )}
              <LandscapeDiorama3D
                baselineMix={baselineMix}
                optimalMix={optimalMix}
              />
            </div>
          )}
        </div>
      </PanelCard>

      {/* Pareto Front & Best Solution Breakdown */}
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr] items-stretch">
        <PanelCard
          id="panel-pareto-front"
          title={t('results_pareto_title')}
          subtitle={t('results_pareto_sub')}
          className="flex flex-col h-full justify-between"
        >
          <div>
            {/* Plain-Language Interpretation for Pareto Front */}
            <div className="mb-4 rounded-xl border border-sky-500/20 bg-sky-500/[0.04] p-3.5 dark:bg-sky-500/[0.08]">
              <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                💡 Cada punto representa una configuración de paisaje distinta que logra un balance diferente entre rendimiento agrícola y abundancia de polinizadores — no existe una única &ldquo;mejor&rdquo; opción, sino distintos compromisos posibles. La estrella verde es la configuración recomendada por el sistema como mejor equilibrio entre ambos objetivos.
              </p>
            </div>

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
          </div>

          {/* Pareto summary footer bar */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50/80 p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-950/50 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-xs" />
              <span>
                Óptimo seleccionado: <strong className="text-slate-900 dark:text-slate-100">{Number(result.best_solution?.crop_yield_index || 0).toFixed(2)}</strong> Rend. / <strong className="text-slate-900 dark:text-slate-100">{Number(result.best_solution?.pollinator_abundance_index || 0).toFixed(2)}</strong> Polin.
              </span>
            </div>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
              {result.pareto_front?.length || 0} configuraciones evaluadas (NSGA-II)
            </div>
          </div>
        </PanelCard>

        <PanelCard
          id="panel-best-solution"
          title={t('results_best_title')}
          subtitle={t('results_best_sub')}
          className="flex flex-col h-full justify-between"
        >
          <div className="space-y-2 text-xs sm:text-sm">
            {Object.entries(result.best_solution)
              .filter(([key]) => !['selection_reason', 'selectionReason', 'Selection_Reason', 'recomendacion_ia'].includes(key))
              .map(([key, value]) => {
                const labels = {
                  crop_yield_index: 'Rendimiento proyectado',
                  pollinator_abundance_index: 'Abundancia polinizadores',
                  crop_area_pct: '% Área de cultivo',
                  natural_area_pct: '% Área natural',
                  floral_strips_pct: '% Franjas florales',
                  pesticide_level: 'Nivel pesticidas',
                  soil_management_score: 'Índice manejo del suelo',
                  landscape_diversity: 'Diversidad del paisaje',
                  pollinator_diversity_index: 'Diversidad polinizadores',
                }
                const displayLabel = labels[key] || key.replace(/_/g, ' ')
                let displayValue = typeof value === 'number' ? value.toFixed(3) : String(value)

                return (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/70 px-3.5 py-2.5 dark:border-slate-800 dark:bg-slate-950/50"
                  >
                    <span className="font-medium text-slate-600 dark:text-slate-300 capitalize">
                      {displayLabel}
                    </span>
                    <span className="font-bold text-slate-900 dark:text-slate-100 font-display text-right">
                      {displayValue}
                    </span>
                  </div>
                )
              })}

            {/* Tarjeta colapsable de Motivo de Selección / Recomendación IA */}
            {(() => {
              const rawReason =
                result.recomendacion_ia ||
                result.best_solution?.selection_reason ||
                result.best_solution?.selectionReason ||
                'Mejor compromiso entre proteger el rendimiento y maximizar la ganancia de polinizadores.'

              const isAiGenerated =
                Boolean(result.recomendacion_ia) ||
                (rawReason &&
                  !rawReason.toLowerCase().includes('best compromise maximizing') &&
                  rawReason.length > 80)

              return (
                <RecommendationAccordion
                  rawReason={rawReason}
                  isAiGenerated={isAiGenerated}
                />
              )
            })()}
          </div>
        </PanelCard>
      </div>

      {/* Trajectory comparison line chart */}
      <PanelCard
        id="panel-trajectory"
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

        {/* Plain-Language Interpretation for Comparative Trajectory */}
        <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-3.5 dark:bg-emerald-500/[0.08]">
          <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
            📈 <strong>Resumen de trayectoria:</strong> La configuración optimizada logra simultáneamente un mayor rendimiento de cultivo (+{result.delta_yield.toFixed(3)}) y una mayor abundancia de polinizadores (+{deltaPollinatorsVal.toFixed(1)}%) respecto al escenario base, sin sacrificar uno por el otro.
          </p>
        </div>
      </PanelCard>
    </div>
  )
}
