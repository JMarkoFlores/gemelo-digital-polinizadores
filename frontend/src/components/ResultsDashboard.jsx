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
import PanelCard from './PanelCard'
import MetricCard from './MetricCard'
import EmptyState from './EmptyState'

function ResultMapCard({ title, data }) {
  const mix = data?.land_use_mix ?? data
  return (
    <div className="rounded-[1.5rem] border border-slate-200 p-4 dark:border-slate-800">
      <p className="text-sm font-medium">{title}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl bg-emerald-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Cultivo</p>
          <p className="mt-2 text-2xl font-semibold">{mix?.crop_area_pct?.toFixed?.(1) ?? 'N/A'}%</p>
        </div>
        <div className="rounded-2xl bg-sky-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Seminatural</p>
          <p className="mt-2 text-2xl font-semibold">{mix?.natural_area_pct?.toFixed?.(1) ?? 'N/A'}%</p>
        </div>
        <div className="rounded-2xl bg-amber-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Franjas florales</p>
          <p className="mt-2 text-2xl font-semibold">{mix?.floral_strips_pct?.toFixed?.(1) ?? 'N/A'}%</p>
        </div>
      </div>
    </div>
  )
}

export default function ResultsDashboard({ result }) {
  if (!result) {
    return <EmptyState title="Resultados pendientes" description="Cuando ejecutes la optimizacion apareceran aqui el frente de Pareto, el paisaje recomendado y los cambios esperados." />
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Delta rendimiento" value={result.delta_yield.toFixed(3)} hint="Cambio estimado del surrogate." />
        <MetricCard label="Delta polinizadores" value={`${result.delta_pollinators.toFixed(1)}%`} hint="Ganancia relativa frente a la linea base." />
        <MetricCard label="Hipotesis" value={result.hypothesis_status} hint="Evaluacion automatica del criterio del articulo." />
        <MetricCard label="Cache" value={result.cache_hit ? 'Hit' : 'Nuevo'} hint={`Modelo ${result.model_version || 'N/A'}`} />
      </div>

      <PanelCard title="Comparacion espacial" subtitle="Representacion agregada del uso del suelo base frente a la recomendacion optimizada.">
        <div className="grid gap-4 xl:grid-cols-2">
          <ResultMapCard title="Paisaje base" data={result.baseline} />
          <ResultMapCard title="Paisaje optimizado" data={result.optimized_landscape} />
        </div>
      </PanelCard>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <PanelCard title="Frente de Pareto" subtitle="Cada punto representa una configuracion no dominada por NSGA-II.">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="crop_yield_index" name="Rendimiento" />
                <YAxis type="number" dataKey="pollinator_abundance_index" name="Polinizadores" />
                <Tooltip cursor={{ strokeDasharray: '4 4' }} />
                <Scatter data={result.pareto_front} fill="#22c55e" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </PanelCard>

        <PanelCard title="Mejor solucion" subtitle="Compromiso seleccionado para proteger rendimiento y mejorar servicios ecosistemicos.">
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

      <PanelCard title="Trayectoria comparativa" subtitle="Comparacion simple entre linea base y solucion elegida para las variables de salida principales.">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={[
                { stage: 'Base', yield: result.baseline.crop_yield_index, pollinators: result.baseline.pollinator_abundance_index },
                { stage: 'Optimo', yield: result.best_solution.crop_yield_index, pollinators: result.best_solution.pollinator_abundance_index },
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
