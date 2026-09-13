import { useTranslation } from 'react-i18next'
import PanelCard from './PanelCard'

export default function ScenarioPanel({ values, onChange, onRun, disabled, loading }) {
  const { t } = useTranslation()

  return (
    <PanelCard
      id="scenario-panel"
      title={t('scenario_title')}
      subtitle={t('scenario_sub')}
      actions={
        <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Parámetros IA Calibrados
        </span>
      }
    >
      <div className="grid gap-4 sm:gap-5 md:grid-cols-3">
        {/* Pesticides Slider */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 transition-all hover:border-slate-300 dark:border-slate-800/80 dark:bg-slate-950/50">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-500/10 text-rose-500">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m14 12-8.5 8.5a2.12 2.12 0 1 1-3-3L11 9"/><path d="M15 13 9 7l4-4 6 6-4 4Z"/><path d="m17 7 3-3"/>
                </svg>
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                {t('scenario_pesticides')}
              </span>
            </div>
            <span className="inline-flex items-center rounded-lg bg-white px-2.5 py-1 text-xs font-bold text-slate-900 shadow-sm dark:bg-slate-800 dark:text-slate-100 font-display">
              {values.pesticide_level}%
            </span>
          </div>

          <div className="space-y-1.5">
            <input
              type="range"
              min="0"
              max="100"
              value={values.pesticide_level}
              onChange={(e) => onChange('pesticide_level', Number(e.target.value))}
              className="w-full h-2"
            />
            <div className="flex justify-between text-[10px] font-semibold text-slate-400">
              <span>0% (Biológico)</span>
              <span>100% (Convencional)</span>
            </div>
          </div>
        </div>

        {/* Natural Area Slider */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 transition-all hover:border-slate-300 dark:border-slate-800/80 dark:bg-slate-950/50">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
                </svg>
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                {t('scenario_naturalArea')}
              </span>
            </div>
            <span className="inline-flex items-center rounded-lg bg-white px-2.5 py-1 text-xs font-bold text-slate-900 shadow-sm dark:bg-slate-800 dark:text-slate-100 font-display">
              {values.min_natural_area_pct}%
            </span>
          </div>

          <div className="space-y-1.5">
            <input
              type="range"
              min="5"
              max="45"
              value={values.min_natural_area_pct}
              onChange={(e) => onChange('min_natural_area_pct', Number(e.target.value))}
              className="w-full h-2"
            />
            <div className="flex justify-between text-[10px] font-semibold text-slate-400">
              <span>5% (Mínimo)</span>
              <span>45% (Corredor amplio)</span>
            </div>
          </div>
        </div>

        {/* Climate Scenario Dropdown */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 transition-all hover:border-slate-300 dark:border-slate-800/80 dark:bg-slate-950/50">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 text-sky-500">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>
              </svg>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              {t('scenario_climate')}
            </span>
          </div>

          <select
            value={values.climate_scenario}
            onChange={(e) => onChange('climate_scenario', e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm font-medium text-slate-900 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="current">{t('scenario_climate_current')}</option>
            <option value="warm">{t('scenario_climate_warm')}</option>
            <option value="dry">{t('scenario_climate_dry')}</option>
            <option value="extreme">{t('scenario_climate_extreme')}</option>
          </select>
        </div>
      </div>

      <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800/60">
        <p className="text-xs text-slate-500 dark:text-slate-400 text-center sm:text-left">
          {disabled
            ? '💡 Dibuja o selecciona un polígono en el mapa para habilitar la optimización'
            : 'Listo para simular la abundancia de polinizadores y rendimiento'}
        </p>

        <button
          id="run-optimization-btn"
          onClick={onRun}
          disabled={disabled || loading}
          className="group relative flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 font-semibold text-white shadow-md transition hover:bg-emerald-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
        >
          {loading ? (
            <>
              <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>{t('scenario_running')}</span>
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-200 group-hover:rotate-12 transition-transform">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>{t('scenario_runBtn')}</span>
            </>
          )}
        </button>
      </div>
    </PanelCard>
  )
}
