import { useTranslation } from 'react-i18next'
import PanelCard from './PanelCard'

export default function ScenarioPanel({ values, onChange, onRun, disabled, loading }) {
  const { t } = useTranslation()
  return (
    <PanelCard title={t('scenario_title')} subtitle={t('scenario_sub')}>
      <div className="grid gap-5 lg:grid-cols-3">
        <label className="space-y-2 rounded-[1.5rem] bg-slate-50 p-4 dark:bg-slate-950/50">
          <span className="text-sm font-medium">{t('scenario_pesticides')}: {values.pesticide_level}%</span>
          <input type="range" min="0" max="100" value={values.pesticide_level} onChange={(e) => onChange('pesticide_level', Number(e.target.value))} className="w-full" />
        </label>
        <label className="space-y-2 rounded-[1.5rem] bg-slate-50 p-4 dark:bg-slate-950/50">
          <span className="text-sm font-medium">{t('scenario_naturalArea')}: {values.min_natural_area_pct}%</span>
          <input type="range" min="5" max="45" value={values.min_natural_area_pct} onChange={(e) => onChange('min_natural_area_pct', Number(e.target.value))} className="w-full" />
        </label>
        <label className="space-y-2 rounded-[1.5rem] bg-slate-50 p-4 dark:bg-slate-950/50">
          <span className="text-sm font-medium">{t('scenario_climate')}</span>
          <select value={values.climate_scenario} onChange={(e) => onChange('climate_scenario', e.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
            <option value="current">{t('scenario_climate_current')}</option>
            <option value="warm">{t('scenario_climate_warm')}</option>
            <option value="dry">{t('scenario_climate_dry')}</option>
            <option value="extreme">{t('scenario_climate_extreme')}</option>
          </select>
        </label>
      </div>
      <div className="mt-5 flex justify-end">
        <button
          onClick={onRun}
          disabled={disabled || loading}
          className="rounded-2xl bg-primary-600 px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? t('scenario_running') : t('scenario_runBtn')}
        </button>
      </div>
    </PanelCard>
  )
}
