import { Suspense, lazy, useMemo, useState } from 'react'
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
  const [geometry, setGeometry] = useState(null)
  const [scenario, setScenario] = useState({ pesticide_level: 30, min_natural_area_pct: 20, climate_scenario: 'current' })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const payload = useMemo(() => ({ geometry, bbox: geometry ? bboxFromGeometry(geometry) : null, ...scenario }), [geometry, scenario])

  const runSimulation = async () => {
    if (!geometry) {
      setError('Primero debes dibujar un area en el mapa.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await api.post('/api/simular', payload)
      setResult(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible ejecutar la optimizacion.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">Cliente</p>
        <h1 className="mt-3 text-4xl font-semibold">Optimizacion de paisaje agricola</h1>
        <p className="mt-2 max-w-3xl text-slate-600 dark:text-slate-300">
          Dibuja tu zona de interes, ajusta restricciones y ejecuta el optimizador multiobjetivo sobre el surrogate entrenado en Streamlit.
        </p>
      </section>
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      {result ? (
        <div className="flex justify-end">
          <button
            onClick={async () => {
              const { exportSimulationToPdf } = await import('../lib/exporters')
              exportSimulationToPdf({ ...result, id: 'resultado' })
            }}
            className="rounded-2xl bg-slate-200 px-4 py-2 text-sm dark:bg-slate-800"
          >
            Exportar resultado actual a PDF
          </button>
        </div>
      ) : null}
      <Suspense fallback={<SpinnerBlock label="Cargando mapa interactivo" />}>
        <MapSelectionCard geometry={geometry} onGeometryChange={setGeometry} baseline={result?.baseline} />
      </Suspense>
      <ScenarioPanel values={scenario} onChange={(key, value) => setScenario((prev) => ({ ...prev, [key]: value }))} onRun={runSimulation} disabled={!geometry} loading={loading} />
      <Suspense fallback={<SpinnerBlock label="Cargando visualizaciones" />}>
        <ResultsDashboard result={result} />
      </Suspense>
    </div>
  )
}
