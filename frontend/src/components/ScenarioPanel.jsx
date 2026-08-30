import PanelCard from './PanelCard'

export default function ScenarioPanel({ values, onChange, onRun, disabled, loading }) {
  return (
    <PanelCard title="Escenario de manejo" subtitle="Ajusta pesticidas, minimo de area natural y escenario climatico antes de enviar la optimizacion.">
      <div className="grid gap-5 lg:grid-cols-3">
        <label className="space-y-2 rounded-[1.5rem] bg-slate-50 p-4 dark:bg-slate-950/50">
          <span className="text-sm font-medium">Nivel de pesticidas: {values.pesticide_level}%</span>
          <input type="range" min="0" max="100" value={values.pesticide_level} onChange={(e) => onChange('pesticide_level', Number(e.target.value))} className="w-full" />
        </label>
        <label className="space-y-2 rounded-[1.5rem] bg-slate-50 p-4 dark:bg-slate-950/50">
          <span className="text-sm font-medium">Area natural minima: {values.min_natural_area_pct}%</span>
          <input type="range" min="5" max="45" value={values.min_natural_area_pct} onChange={(e) => onChange('min_natural_area_pct', Number(e.target.value))} className="w-full" />
        </label>
        <label className="space-y-2 rounded-[1.5rem] bg-slate-50 p-4 dark:bg-slate-950/50">
          <span className="text-sm font-medium">Escenario climatico</span>
          <select value={values.climate_scenario} onChange={(e) => onChange('climate_scenario', e.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
            <option value="current">Actual</option>
            <option value="warm">Calido</option>
            <option value="dry">Seco</option>
            <option value="extreme">Extremo</option>
          </select>
        </label>
      </div>
      <div className="mt-5 flex justify-end">
        <button
          onClick={onRun}
          disabled={disabled || loading}
          className="rounded-2xl bg-primary-600 px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? 'Optimizando...' : 'Optimizar paisaje'}
        </button>
      </div>
    </PanelCard>
  )
}
