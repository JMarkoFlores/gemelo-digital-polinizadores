import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

function checkGeographicValidity(geom, bounds, regName) {
  if (!geom) {
    return { isValid: true, hasRestriction: !!bounds, distanceKm: null, maxAllowedKm: null, message: null }
  }
  if (!bounds || typeof bounds.lat !== 'number' || typeof bounds.lon !== 'number' || typeof bounds.radius_km !== 'number') {
    // Modelo sintético o sin metadatos de coordenadas: sin restricción geográfica
    return { isValid: true, hasRestriction: false, distanceKm: null, maxAllowedKm: null, message: null }
  }

  const coords = geom?.coordinates?.[0] || []
  if (!coords.length) {
    return { isValid: true, hasRestriction: true, distanceKm: null, maxAllowedKm: bounds.radius_km * 1.2, message: null }
  }

  let sumLon = 0, sumLat = 0
  for (const [lon, lat] of coords) {
    sumLon += lon
    sumLat += lat
  }
  const centroidLat = sumLat / coords.length
  const centroidLon = sumLon / coords.length

  // Distancia Haversine en kilómetros
  const R = 6371.0
  const dLat = ((centroidLat - bounds.lat) * Math.PI) / 180
  const dLon = ((centroidLon - bounds.lon) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((bounds.lat * Math.PI) / 180) *
      Math.cos((centroidLat * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  const distanceKm = Math.round(R * c * 10) / 10
  const maxAllowedKm = Math.round(bounds.radius_km * 1.2 * 10) / 10

  const isValid = distanceKm <= maxAllowedKm
  const message = isValid
    ? null
    : `⚠️ Esta área está fuera de la región para la que el modelo activo fue entrenado y validado (${regName || 'Región calibrada'}). Distancia observada: ${distanceKm} km (radio máximo permitido con tolerancia: ${maxAllowedKm} km). Los resultados no serían científicamente válidos. Entrena y activa un modelo para tu región en Streamlit antes de continuar.`

  return {
    isValid,
    hasRestriction: true,
    distanceKm,
    maxAllowedKm,
    centroid: { lat: centroidLat, lon: centroidLon },
    message,
  }
}

export default function ClientOptimizePage() {
  const { t } = useTranslation()
  const [geometry, setGeometry] = useState(null)
  const [scenario, setScenario] = useState({ pesticide_level: 30, min_natural_area_pct: 20, climate_scenario: 'current' })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [connectionState, setConnectionState] = useState('checking') // 'checking' | 'connected' | 'error'
  const [connectionError, setConnectionError] = useState('')
  const [modelReady, setModelReady] = useState(null)   // null = checking, true/false = known
  const [modelStatus, setModelStatus] = useState('')
  const [reloading, setReloading] = useState(false)
  const [modelName, setModelName] = useState('')
  const [modelVersion, setModelVersion] = useState('')
  const [regionName, setRegionName] = useState(null)
  const [regionBounds, setRegionBounds] = useState(null)
  const [fuenteDatos, setFuenteDatos] = useState(null)
  const [elevationData, setElevationData] = useState(null)
  const [modelUpdateNotice, setModelUpdateNotice] = useState(null)

  const lastVersionRef = useRef(null)
  const lastReadyRef = useRef(null)
  const isDrawingRef = useRef(false)
  const loadingRef = useRef(false)
  const retryCountRef = useRef(0)
  loadingRef.current = loading

  const handleDrawingChange = useCallback((isDrawing) => {
    isDrawingRef.current = isDrawing
  }, [])

  const fetchElevation = async (geom) => {
    if (!geom) {
      setElevationData(null)
      return
    }
    try {
      const res = await api.post('/api/terrain/elevation-grid', { geometry: geom })
      setElevationData(res.data)
    } catch (err) {
      console.warn('Error al consultar elevación real:', err)
      setElevationData({
        available: false,
        source: 'Fallback estándar',
        min_elevation_m: 0,
        max_elevation_m: 0,
        elevation_range_m: 0,
        mean_elevation_m: 0,
        grid: [],
        matrix: Array(10).fill(Array(10).fill(0)),
        normalized_matrix: Array(10).fill(Array(10).fill(0)),
        message: 'Relieve no disponible para esta zona, mostrando vista plana.',
      })
    }
  }

  const handleGeometryChange = useCallback((newGeom) => {
    setGeometry(newGeom)
    setError('')
    if (newGeom) {
      fetchElevation(newGeom)
    } else {
      setElevationData(null)
    }
  }, [])

  const checkModelStatus = useCallback(async (isManual = false) => {
    // Si el usuario está interactuando activamente, omitir tick para no interrumpir
    if (!isManual && (isDrawingRef.current || loadingRef.current)) {
      return
    }

    try {
      // Usamos /health que es ultra liviano y reporta el estado y versión actual en memoria
      const res = await api.get('/health', { timeout: 8000 })
      const data = res.data
      const newVersion = data.model_version ?? data.version ?? ''
      const isReady = Boolean(data.model_ready)
      const newName = data.model_name ?? ''
      const newStatus = data.model_status ?? ''
      const newRegion = data.region_name ?? null
      const newBounds = data.region_bounds ?? null
      const newFuente = data.fuente_datos ?? null

      // Si el modelo cambió respecto al registrado en el frontend
      if (lastVersionRef.current && newVersion && newVersion !== lastVersionRef.current) {
        const displayLabel = newRegion ? `${newRegion} (${newVersion})` : newVersion
        setModelUpdateNotice(`✅ Modelo actualizado: ahora usando ${displayLabel}`)
        setTimeout(() => {
          setModelUpdateNotice((prev) => (prev && prev.includes(newVersion) ? null : prev))
        }, 7000)
      } else if (lastReadyRef.current === false && isReady) {
        const displayLabel = newRegion ? `${newRegion} (${newVersion})` : (newVersion || 'nuevo modelo')
        setModelUpdateNotice(`✅ Modelo entrenado y cargado con éxito: ${displayLabel}`)
        setTimeout(() => setModelUpdateNotice(null), 7000)
      }

      if (newVersion) {
        lastVersionRef.current = newVersion
      }
      lastReadyRef.current = isReady
      retryCountRef.current = 0

      setConnectionState('connected')
      setConnectionError('')
      setModelReady(isReady)
      setModelName(newName)
      setModelStatus(newStatus)
      setModelVersion(newVersion)
      setRegionName(newRegion)
      setRegionBounds(newBounds)
      setFuenteDatos(newFuente)
    } catch {
      // Fallback a /api/model/status si /health falla por cualquier eventualidad
      try {
        const res = await api.get('/api/model/status', { timeout: 8000 })
        const data = res.data
        const newVersion = data.model_version ?? data.version ?? ''
        const isReady = Boolean(data.model_ready)

        if (lastVersionRef.current && newVersion && newVersion !== lastVersionRef.current) {
          const displayLabel = data.region_name ? `${data.region_name} (${newVersion})` : newVersion
          setModelUpdateNotice(`✅ Modelo actualizado: ahora usando ${displayLabel}`)
          setTimeout(() => {
            setModelUpdateNotice((prev) => (prev && prev.includes(newVersion) ? null : prev))
          }, 7000)
        } else if (lastReadyRef.current === false && isReady) {
          const displayLabel = data.region_name ? `${data.region_name} (${newVersion})` : (newVersion || 'nuevo modelo')
          setModelUpdateNotice(`✅ Modelo entrenado y cargado con éxito: ${displayLabel}`)
          setTimeout(() => setModelUpdateNotice(null), 7000)
        }

        if (newVersion) lastVersionRef.current = newVersion
        lastReadyRef.current = isReady
        retryCountRef.current = 0

        setConnectionState('connected')
        setConnectionError('')
        setModelReady(isReady)
        setModelName(data.model_name ?? '')
        setModelStatus(data.model_status ?? '')
        setModelVersion(newVersion)
        setRegionName(data.region_name ?? null)
        setRegionBounds(data.region_bounds ?? null)
        setFuenteDatos(data.fuente_datos ?? null)
      } catch (fallbackErr) {
        // Si el backend está arrancando y es la primera consulta, reintentar con backoff corto
        if (!isManual && retryCountRef.current < 2 && lastReadyRef.current === null) {
          retryCountRef.current += 1
          const backoff = retryCountRef.current * 2000
          setTimeout(() => checkModelStatus(), backoff)
          return
        }

        setConnectionState('error')
        setConnectionError('No se pudo establecer conexión con el servidor backend. Verifica que el servicio esté activo.')
      }
    }
  }, [])

  // Check model readiness on mount de inmediato y polling regular cada 15s para detectar modelos entrenados en Streamlit
  useEffect(() => {
    checkModelStatus(true)
    const interval = setInterval(() => checkModelStatus(false), 15000)
    return () => clearInterval(interval)
  }, [checkModelStatus])

  const handleManualReload = async () => {
    setReloading(true)
    try {
      const res = await api.post('/api/model/reload')
      const newVersion = res.data.model_version ?? res.data.version ?? ''
      const isReady = Boolean(res.data.model_ready)
      if (newVersion) lastVersionRef.current = newVersion
      lastReadyRef.current = isReady
      setConnectionState('connected')
      setConnectionError('')
      setModelReady(isReady)
      setModelStatus(res.data.model_status ?? '')
      setModelVersion(newVersion)
      setRegionName(res.data.region_name ?? null)
      setRegionBounds(res.data.region_bounds ?? null)
      setFuenteDatos(res.data.fuente_datos ?? null)
    } catch {
      await checkModelStatus(true)
    } finally {
      setReloading(false)
    }
  }

  // Validación de alcance geográfico (Domain Shift)
  const geoValidation = useMemo(
    () => checkGeographicValidity(geometry, regionBounds, regionName),
    [geometry, regionBounds, regionName]
  )

  const payload = useMemo(
    () => ({ geometry, bbox: geometry ? bboxFromGeometry(geometry) : null, ...scenario }),
    [geometry, scenario]
  )

  const runSimulation = async () => {
    if (!geometry) {
      setError(t('clientOpt_errorNoGeom'))
      return
    }
    if (!geoValidation.isValid) {
      setError(geoValidation.message)
      return
    }
    setLoading(true)
    setError('')
    try {
      const [response] = await Promise.all([
        api.post('/api/simular', payload),
        fetchElevation(geometry),
      ])
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

      {/* Discrete Notification Toast for Hot Reloaded Model */}
      {modelUpdateNotice && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-300 rounded-xl bg-emerald-500/15 border border-emerald-500/40 px-4 py-2.5 text-xs sm:text-sm font-semibold text-emerald-800 dark:text-emerald-200 flex items-center justify-between shadow-xs">
          <span className="flex items-center gap-2">
            <span>{modelUpdateNotice}</span>
          </span>
          <button
            type="button"
            onClick={() => setModelUpdateNotice(null)}
            className="text-emerald-700 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-100 text-xs font-bold px-2 py-0.5 rounded cursor-pointer"
            title="Cerrar aviso"
          >
            ✕
          </button>
        </div>
      )}

      {/* 1. Cargando / Conectando con backend */}
      {connectionState === 'checking' && (
        <StatusBanner tone="info">
          <div className="flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin text-sky-500 shrink-0" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span>Verificando estado del modelo IA y conexión con el backend…</span>
          </div>
        </StatusBanner>
      )}

      {/* 2. Error de conexión con el backend (distinto a 'sin modelo') */}
      {connectionState === 'error' && (
        <StatusBanner tone="error">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <strong>🔌 Error de conexión con el backend:</strong> {connectionError || 'No se pudo comunicar con el servidor API. Verifica que el contenedor backend esté en ejecución.'}
            </div>
            <button
              onClick={() => {
                setConnectionState('checking')
                checkModelStatus(true)
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-800 hover:bg-rose-500/30 transition dark:text-rose-200 shrink-0"
            >
              🔄 Reintentar conexión
            </button>
          </div>
        </StatusBanner>
      )}

      {/* 3. Backend conectado pero SIN MODELO ENTRENADO */}
      {connectionState === 'connected' && modelReady === false && (
        <StatusBanner tone="warning">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="font-bold text-amber-900 dark:text-amber-200 flex items-center gap-2">
                <span>⚠️ No hay ningún modelo entrenado activo</span>
              </div>
              <p className="text-xs text-amber-800/90 dark:text-amber-300/90 leading-relaxed">
                {modelStatus || 'Para optimizar paisajes agroecológicos, primero debes entrenar y exportar un modelo subrogado desde la plataforma Streamlit.'}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <a
                href={`http://${window.location.hostname}:8501`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-xl bg-amber-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-amber-500 transition"
                title="Abrir Streamlit en el puerto 8501 para entrenar el modelo"
              >
                🚀 Entrenar en Streamlit (8501) →
              </a>
              <button
                onClick={handleManualReload}
                disabled={reloading}
                className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-white/70 px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-white transition disabled:opacity-50 dark:bg-slate-900/60 dark:text-amber-200 dark:hover:bg-slate-900"
              >
                {reloading ? '⏳ Recargando...' : '🔄 Forzar recarga'}
              </button>
            </div>
          </div>
        </StatusBanner>
      )}

      {/* 4. Backend conectado y MODELO ACTIVO */}
      {connectionState === 'connected' && modelReady === true && (
        <StatusBanner tone="success">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span>
                <strong>Modelo IA operativo:</strong> {modelName || modelStatus || 'Modelo subrogado listo para inferencia.'}
                {modelVersion && ` (${modelVersion})`}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {regionBounds ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/15 border border-sky-500/30 px-3 py-1 text-xs font-bold text-sky-800 dark:text-sky-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-sky-500" />
                  📍 Calibrado: {regionName} (Radio: {regionBounds.radius_km} km)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-500/15 border border-purple-500/30 px-3 py-1 text-xs font-bold text-purple-800 dark:text-purple-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                  🧪 Modelo Sintético (Sin restricción espacial)
                </span>
              )}
            </div>
          </div>
        </StatusBanner>
      )}

      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      {/* Step 1: Map Selection */}
      <Suspense fallback={<SpinnerBlock label={t('clientOpt_loadingMap')} />}>
        <MapSelectionCard
          geometry={geometry}
          onGeometryChange={handleGeometryChange}
          onDrawingChange={handleDrawingChange}
          baseline={result?.baseline}
          regionBounds={regionBounds}
          regionName={regionName}
          isAreaValid={geoValidation.isValid}
          validationDistanceKm={geoValidation.distanceKm}
          validationMaxKm={geoValidation.maxAllowedKm}
          validationMessage={geoValidation.message}
        />
      </Suspense>

      {/* Step 2: Scenario Parameters */}
      <ScenarioPanel
        values={scenario}
        onChange={(key, value) => setScenario((prev) => ({ ...prev, [key]: value }))}
        onRun={runSimulation}
        disabled={!geometry || !modelReady || !geoValidation.isValid}
        loading={loading}
        isAreaValid={geoValidation.isValid}
        validationMessage={geoValidation.message}
        regionName={regionName}
        hasRestriction={geoValidation.hasRestriction}
        modelReady={modelReady === true}
        hasGeometry={Boolean(geometry)}
      />

      {/* Step 3: Optimization Results */}
      <Suspense fallback={<SpinnerBlock label={t('clientOpt_loadingViz')} />}>
        <ResultsDashboard result={result} elevationData={elevationData} />
      </Suspense>
    </div>
  )
}
