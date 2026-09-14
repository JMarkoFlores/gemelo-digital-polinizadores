import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../lib/api'
import SpinnerBlock from '../components/SpinnerBlock'
const MapSelectionCard = lazy(() => import('../components/MapSelectionCard'))
const ResultsDashboard = lazy(() => import('../components/ResultsDashboard'))
import ScenarioPanel from '../components/ScenarioPanel'
import StatusBanner from '../components/StatusBanner'

function bboxFromGeometry(geometry) {
  const coordinates = geometry?.coordinates?.[0] || []
  const lons = coordinates.map(([lon]) => lon)
  const lats = coordinates.map(([, lat]) => lat)
  if (!coordinates.length) return null
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)]
}

export default function ClientOptimizePage() {
  const { t } = useTranslation()
  const [geometry, setGeometry] = useState(null)
  const [scenario, setScenario] = useState({ pesticide_level: 30, min_natural_area_pct: 20, climate_scenario: 'current' })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [modelReady, setModelReady] = useState(null)   // null = checking, true/false = known
  const [modelStatus, setModelStatus] = useState('')
  const [reloading, setReloading] = useState(false)
  const [modelName, setModelName] = useState('')
  const [modelVersion, setModelVersion] = useState('')

  const checkModelStatus = () => {
    return api.get('/api/model/status')
      .then((res) => {
        setModelReady(res.data.model_ready)
        setModelName(res.data.model_name ?? '')
        setModelStatus(res.data.model_status ?? '')
        setModelVersion(res.data.model_version ?? res.data.version ?? '')
      })
      .catch(() => {
        setModelReady(false)
        setModelStatus('No se pudo verificar el estado del modelo IA.')
      })
  }

  // Check model readiness on mount and poll
  useEffect(() => {
    checkModelStatus()
    let interval = null
    if (modelReady === false) {
      interval = setInterval(checkModelStatus, 8000)
    }
    return () => clearInterval(interval)
  }, [modelReady])

  const handleManualReload = async () => {
    setReloading(true)
    try {
      const res = await api.post('/api/model/reload')
      setModelReady(res.data.model_ready)
      setModelStatus(res.data.model_status ?? '')
    } catch {
      await checkModelStatus()
    } finally {
      setReloading(false)
    }
  }

  const payload = useMemo(() => ({ geometry, bbox: geometry ? bboxFromGeometry(geometry) : null, ...scenario }), [geometry, scenario])

  const runSimulation = async () => {
    if (!geometry) {
      setError(t('clientOpt_errorNoGeom'))
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await api.post('/api/simular', payload)
      setResult(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || t('clientOpt_errorRun'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header section with badge */}
      <section className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {t('clientOpt_badge')}
            </span>
            <span className="text-xs text-slate-400">Simulación Espacial Multiobjetivo</span>
          </div>
          <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-display">
            {t('clientOpt_title')}
          </h1>
          <p className="mt-1.5 max-w-3xl text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
            {t('clientOpt_desc')}
          </p>
        </div>

        {result ? (
          <button
            id="export-pdf-top-btn"
            onClick={async () => {
              const { exportSimulationToPdf } = await import('../lib/exporters')
              exportSimulationToPdf({ ...result, id: 'resultado' })
            }}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs sm:text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 shrink-0"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-500">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span>{t('clientOpt_exportPdf')}</span>
          </button>
        ) : null}
      </section>

      {/* Model status banner */}
      {modelReady === null && (
        <StatusBanner tone="info">Verificando estado del modelo IA…</StatusBanner>
      )}
      {modelReady === false && (
        <StatusBanner tone="warning">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <strong>⚠️ Modelo IA no cargado:</strong> {modelStatus || 'Verifica el pipeline de exportación.'}
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-2 sm:mt-0">
              <a
                href={`http://${window.location.hostname}:8501`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-500/20 px-3 py-1 text-xs font-bold text-blue-900 hover:bg-blue-500/30 transition dark:text-blue-200 shrink-0"
                title="Abrir Streamlit en una nueva pestaña para entrenar el modelo"
              >
                🚀 Entrenar en Streamlit
              </a>
              <button
                onClick={handleManualReload}
                disabled={reloading}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/20 px-3 py-1 text-xs font-bold text-amber-900 hover:bg-amber-500/30 transition disabled:opacity-50 dark:text-amber-200 shrink-0"
              >
                {reloading ? '⏳ Recargando...' : '🔄 Forzar recarga'}
              </button>
            </div>
          </div>
        </StatusBanner>
      )}
      {modelReady === true && (
        <StatusBanner tone="success">
          <div className="flex items-center justify-between">
            <span>
              <strong>Modelo IA operativo:</strong> {modelName || modelStatus || 'Modelo subrogado listo para inferencia instantánea.'}
              {modelVersion && ` (Versión: ${modelVersion})`}
            </span>
          </div>
        </StatusBanner>
      )}

      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      {/* Step 1: Map Selection */}
      <Suspense fallback={<SpinnerBlock label={t('clientOpt_loadingMap')} />}>
        <MapSelectionCard geometry={geometry} onGeometryChange={setGeometry} baseline={result?.baseline} />
      </Suspense>

      {/* Step 2: Scenario Parameters */}
      <ScenarioPanel
        values={scenario}
        onChange={(key, value) => setScenario((prev) => ({ ...prev, [key]: value }))}
        onRun={runSimulation}
        disabled={!geometry || !modelReady}
        loading={loading}
      />

      {/* Step 3: Optimization Results */}
      <Suspense fallback={<SpinnerBlock label={t('clientOpt_loadingViz')} />}>
        <ResultsDashboard result={result} />
      </Suspense>
    </div>
  )
}
