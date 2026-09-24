import { useEffect, useMemo, useRef, useState } from 'react'
import { Circle, FeatureGroup, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { useTranslation } from 'react-i18next'
import 'leaflet-draw'
import L from '../lib/leaflet'
import PanelCard from './PanelCard'
import StatusBanner from './StatusBanner'

// Workaround for Leaflet.draw bug: "type is not defined" inside readableArea in strict mode
if (typeof window !== 'undefined') {
  window.type = ''
}

const PRESETS = [
  {
    id: 'viru',
    name: 'Valle de Virú (Trujillo)',
    desc: 'La Libertad, Perú (Palto y Arándano)',
    center: [-8.095, -78.85],
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [-78.88, -8.07],
          [-78.82, -8.07],
          [-78.82, -8.12],
          [-78.88, -8.12],
          [-78.88, -8.07],
        ],
      ],
    },
  },
  {
    id: 'ica',
    name: 'Valle de Ica',
    desc: 'Ica, Perú (Vid y Frutales)',
    center: [-14.075, -75.73],
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [-75.76, -14.05],
          [-75.70, -14.05],
          [-75.70, -14.10],
          [-75.76, -14.10],
          [-75.76, -14.05],
        ],
      ],
    },
  },
]

function MapController({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    if (center && center[0] !== undefined && center[1] !== undefined) {
      map.setView(center, zoom || map.getZoom(), { animate: true })
    }
  }, [center, zoom, map])
  return null
}

function DrawControl({ onChange, externalGeometry }) {
  const map = useMap()
  const featureGroupRef = useRef(null)

  useEffect(() => {
    const featureGroup = new L.FeatureGroup()
    featureGroupRef.current = featureGroup
    map.addLayer(featureGroup)

    const drawControl = new L.Control.Draw({
      edit: { featureGroup },
      draw: {
        rectangle: {
          shapeOptions: {
            color: '#10b981',
            fillColor: '#10b981',
            fillOpacity: 0.25,
            weight: 2,
          },
        },
        polygon: {
          allowIntersection: false,
          showArea: true,
          shapeOptions: {
            color: '#10b981',
            fillColor: '#10b981',
            fillOpacity: 0.25,
            weight: 2,
          },
        },
        circle: false,
        circlemarker: false,
        marker: false,
        polyline: false,
      },
    })

    map.addControl(drawControl)

    const handleCreate = (event) => {
      featureGroup.clearLayers()
      featureGroup.addLayer(event.layer)
      onChange(event.layer.toGeoJSON().geometry)
    }

    const handleEdit = () => {
      const layers = featureGroup.getLayers()
      if (layers[0]) {
        onChange(layers[0].toGeoJSON().geometry)
      }
    }

    const handleDelete = () => onChange(null)

    map.on(L.Draw.Event.CREATED, handleCreate)
    map.on(L.Draw.Event.EDITED, handleEdit)
    map.on(L.Draw.Event.DELETED, handleDelete)

    return () => {
      map.off(L.Draw.Event.CREATED, handleCreate)
      map.off(L.Draw.Event.EDITED, handleEdit)
      map.off(L.Draw.Event.DELETED, handleDelete)
      map.removeControl(drawControl)
      map.removeLayer(featureGroup)
    }
  }, [map, onChange])

  // Sync external geometry when preset is clicked
  useEffect(() => {
    if (!featureGroupRef.current) return
    featureGroupRef.current.clearLayers()
    if (externalGeometry) {
      try {
        const geoJsonLayer = L.geoJSON(externalGeometry, {
          style: {
            color: '#10b981',
            fillColor: '#10b981',
            fillOpacity: 0.25,
            weight: 2,
          },
        })
        geoJsonLayer.eachLayer((l) => featureGroupRef.current.addLayer(l))
        const bounds = geoJsonLayer.getBounds()
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [30, 30] })
        }
      } catch (e) {
        // ignore parse errors
      }
    }
  }, [externalGeometry, map])

  return <FeatureGroup />
}

export default function MapSelectionCard({
  geometry,
  onGeometryChange,
  baseline,
  regionBounds = null,
  regionName = null,
  isAreaValid = true,
  validationDistanceKm = null,
  validationMaxKm = null,
  validationMessage = null,
}) {
  const { t } = useTranslation()
  const initialCenter = regionBounds ? [regionBounds.lat, regionBounds.lon] : [-8.08, -78.85]
  const [view, setView] = useState(initialCenter)
  const [zoomLevel, setZoomLevel] = useState(regionBounds ? 10 : 11)
  const [showRawJson, setShowRawJson] = useState(false)
  const [copied, setCopied] = useState(false)

  // Update view when regionBounds becomes available if no geometry exists yet
  useEffect(() => {
    if (regionBounds?.lat && regionBounds?.lon && !geometry && !baseline) {
      setView([regionBounds.lat, regionBounds.lon])
      setZoomLevel(10)
    }
  }, [regionBounds, geometry, baseline])

  useEffect(() => {
    if (baseline?.geometry?.coordinates?.[0]?.[0]) {
      const [lng, lat] = baseline.geometry.coordinates[0][0]
      setView([lat, lng])
    }
  }, [baseline])

  const copyGeoJson = () => {
    if (!geometry) return
    navigator.clipboard.writeText(JSON.stringify(geometry, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const coordinatesCount = (() => {
    const coords = geometry?.coordinates?.[0]
    if (!coords || coords.length === 0) return 0
    const first = coords[0]
    const last = coords[coords.length - 1]
    const isClosed = first[0] === last[0] && first[1] === last[1] && coords.length > 2
    return isClosed ? coords.length - 1 : coords.length
  })()

  // Preset dinámico que cae exactamente dentro del círculo válido del modelo activo
  const activeRegionPreset = useMemo(() => {
    if (!regionBounds) return null
    const lat = regionBounds.lat
    const lon = regionBounds.lon
    const delta = 0.035
    return {
      id: 'active_region_preset',
      name: `${regionName ? regionName.split('(')[0].trim() : 'Zona Calibrada'} (Válido)`,
      desc: `Parcela de prueba calibrada para ${regionName || 'el modelo activo'}`,
      center: [lat, lon],
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [Number((lon - delta).toFixed(4)), Number((lat - delta).toFixed(4))],
            [Number((lon + delta).toFixed(4)), Number((lat - delta).toFixed(4))],
            [Number((lon + delta).toFixed(4)), Number((lat + delta).toFixed(4))],
            [Number((lon - delta).toFixed(4)), Number((lat + delta).toFixed(4))],
            [Number((lon - delta).toFixed(4)), Number((lat - delta).toFixed(4))],
          ],
        ],
      },
    }
  }, [regionBounds, regionName])

  return (
    <PanelCard
      id="map-selection-card"
      title={t('map_title')}
      subtitle={t('map_sub')}
      actions={
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 mr-1 hidden sm:inline">
            Estado:
          </span>
          {geometry ? (
            isAreaValid ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {coordinatesCount} vértices (Válido)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-bold text-rose-600 dark:text-rose-400 animate-pulse">
                <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                {coordinatesCount} vértices (Fuera de zona)
              </span>
            )
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-600 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
              Esperando delimitación
            </span>
          )}
        </div>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[1.45fr_0.85fr]">
        {/* Map column */}
        <div className="space-y-3">
          <div className="relative h-[420px] sm:h-[460px] overflow-hidden rounded-2xl border border-slate-200/90 shadow-sm dark:border-slate-800">
            <MapContainer center={view} zoom={zoomLevel} scrollWheelZoom className="z-0 h-full w-full">
              <MapController center={view} zoom={zoomLevel} />
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Zona de validez agroecológica del modelo activo */}
              {regionBounds && (
                <Circle
                  center={[regionBounds.lat, regionBounds.lon]}
                  radius={regionBounds.radius_km * 1000}
                  pathOptions={{
                    color: '#0284c7',
                    fillColor: '#38bdf8',
                    fillOpacity: 0.16,
                    dashArray: '6, 6',
                    weight: 2,
                  }}
                >
                  <Tooltip direction="top" permanent={false} className="text-xs font-semibold">
                    📍 Zona válida: {regionName || 'Región calibrada'} ({regionBounds.radius_km} km)
                  </Tooltip>
                </Circle>
              )}

              <DrawControl onChange={onGeometryChange} externalGeometry={geometry} />
            </MapContainer>

            {/* Drawing instruction / Geographic scope floating badge */}
            <div className="pointer-events-none absolute bottom-3 left-3 right-3 sm:right-auto z-[400] flex flex-col gap-1.5">
              {regionBounds ? (
                <div className="rounded-xl border border-sky-300/80 bg-white/95 px-3 py-1.5 text-xs font-medium text-sky-800 shadow-md backdrop-blur-md dark:border-sky-700/80 dark:bg-slate-900/95 dark:text-sky-200">
                  📍 <strong>Zona válida del modelo:</strong> {regionName} (Círculo azul, radio {regionBounds.radius_km} km)
                </div>
              ) : (
                <div className="rounded-xl border border-purple-300/80 bg-white/95 px-3 py-1.5 text-xs font-medium text-purple-800 shadow-md backdrop-blur-md dark:border-purple-700/80 dark:bg-slate-900/95 dark:text-purple-200">
                  🧪 <strong>Modelo sintético:</strong> Puedes delimitar en cualquier ubicación geográfica
                </div>
              )}
              <div className="rounded-xl border border-slate-200/80 bg-white/95 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-md backdrop-blur-md dark:border-slate-700/80 dark:bg-slate-900/95 dark:text-slate-200">
                ✏️ Usa la barra izquierda para dibujar un <strong>polígono</strong> o <strong>rectángulo</strong>
              </div>
            </div>
          </div>

          {/* Preset Buttons Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Preajustes Rápidos:
              </span>

              {/* Botón dinámico para la región activa válida */}
              {activeRegionPreset && (
                <button
                  type="button"
                  onClick={() => {
                    setView(activeRegionPreset.center)
                    setZoomLevel(10)
                    onGeometryChange(activeRegionPreset.geometry)
                  }}
                  className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800 shadow-xs transition hover:bg-emerald-100 hover:border-emerald-500 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 dark:hover:bg-emerald-900/60"
                  title="Cargar polígono de prueba dentro del área válida del modelo activo"
                >
                  🎯 {activeRegionPreset.name}
                </button>
              )}

              {/* Botón para enfocar la zona válida */}
              {regionBounds && (
                <button
                  type="button"
                  onClick={() => {
                    setView([regionBounds.lat, regionBounds.lon])
                    setZoomLevel(10)
                  }}
                  className="rounded-xl border border-sky-200 bg-sky-50/70 px-2.5 py-1.5 text-xs font-medium text-sky-700 hover:bg-sky-100 dark:border-sky-800 dark:bg-slate-900 dark:text-sky-300"
                  title="Centrar mapa en la zona de validez del modelo activo"
                >
                  🔍 Centrar en {regionName?.split('(')[0]?.trim() || 'zona'}
                </button>
              )}

              {/* Presets fijos para contrastar y demostrar el bloqueo */}
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    setView(p.center)
                    setZoomLevel(11)
                    onGeometryChange(p.geometry)
                  }}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-xs transition hover:border-emerald-500 hover:text-emerald-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-emerald-500 dark:hover:text-emerald-400"
                  title={p.desc}
                >
                  📍 {p.name}
                </button>
              ))}
            </div>

            {geometry && (
              <button
                type="button"
                onClick={() => onGeometryChange(null)}
                className="text-xs font-medium text-rose-500 hover:text-rose-600 underline"
              >
                Limpiar área
              </button>
            )}
          </div>
        </div>

        {/* Sidebar Info column */}
        <div className="flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            {geometry ? (
              <StatusBanner tone={isAreaValid ? 'success' : 'error'}>
                {isAreaValid ? t('map_captured') : '⚠️ Área fuera de la región válida del modelo'}
              </StatusBanner>
            ) : (
              <StatusBanner tone="info">{t('map_drawPrompt')}</StatusBanner>
            )}

            {/* Geographic Scope Validation Alert */}
            {geometry && regionBounds && (
              isAreaValid ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-3 text-xs text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300">
                  <div className="flex items-center gap-1.5 font-bold">
                    <span>✅</span>
                    <span>Área Geográficamente Válida</span>
                  </div>
                  <p className="mt-1 text-[11px] text-emerald-700 dark:text-emerald-400 leading-relaxed">
                    El centroide está a <strong>{validationDistanceKm?.toFixed(1)} km</strong> del centro de <em>{regionName}</em> (máx. permitido con tolerancia: <strong>{validationMaxKm?.toFixed(1)} km</strong>). Validez ecológica asegurada.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-rose-300 bg-rose-50 p-3.5 text-xs text-rose-950 dark:border-rose-900/60 dark:bg-rose-950/60 dark:text-rose-200 shadow-xs">
                  <div className="flex items-start gap-2">
                    <span className="text-lg shrink-0">⚠️</span>
                    <div>
                      <p className="font-bold text-rose-800 dark:text-rose-300">
                        Bloqueo por Validez Científica (Domain Shift)
                      </p>
                      <p className="mt-1 text-[11px] leading-relaxed text-rose-900 dark:text-rose-200">
                        {validationMessage}
                      </p>
                    </div>
                  </div>
                </div>
              )
            )}

            {geometry && !regionBounds && (
              <div className="rounded-xl border border-purple-200 bg-purple-50/80 p-3 text-xs text-purple-800 dark:border-purple-900/50 dark:bg-purple-950/40 dark:text-purple-300">
                <div className="flex items-center gap-1.5 font-bold">
                  <span>🧪</span>
                  <span>Modelo Sintético (Sin restricción espacial)</span>
                </div>
                <p className="mt-0.5 text-[11px] text-purple-700 dark:text-purple-400 leading-relaxed">
                  Permite simular en cualquier ubicación, pero no cuenta con calibración agroecológica empírica.
                </p>
              </div>
            )}

            {/* Geometry info card */}
            <div className="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 dark:border-slate-800/80 dark:bg-slate-950/50">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  {t('map_currentGeoJson')}
                </span>
                <div className="flex items-center gap-2">
                  {geometry && (
                    <button
                      type="button"
                      onClick={copyGeoJson}
                      className="text-[11px] font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 underline"
                    >
                      {copied ? '✓ Copiado' : 'Copiar GeoJSON'}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowRawJson(!showRawJson)}
                    className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 underline"
                  >
                    {showRawJson ? 'Ocultar JSON' : 'Ver JSON'}
                  </button>
                </div>
              </div>

              {/* Summary representation */}
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-xl bg-white p-2.5 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                  <p className="text-slate-400">Tipo de Geometría</p>
                  <p className="mt-0.5 font-bold text-slate-800 dark:text-slate-200 font-display">
                    {geometry?.type || 'Ninguna'}
                  </p>
                </div>
                <div className="rounded-xl bg-white p-2.5 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                  <p className="text-slate-400">Vértices Registrados</p>
                  <p className="mt-0.5 font-bold text-slate-800 dark:text-slate-200 font-display">
                    {coordinatesCount}
                  </p>
                </div>
              </div>

              {/* Raw JSON expandable */}
              {showRawJson && (
                <div className="mt-3">
                  <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-900 p-3 text-[11px] text-emerald-300 font-mono">
                    {geometry ? JSON.stringify(geometry, null, 2) : t('map_noGeom')}
                  </pre>
                </div>
              )}
            </div>

            {/* Baseline metrics card if available */}
            {baseline ? (
              <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                    {t('map_baselineTitle')}
                  </span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    Línea Base Inicial
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-950/60">
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t('map_yield')}</p>
                    <p className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100 font-display">
                      {baseline.crop_yield_index?.toFixed?.(3) ?? baseline.crop_yield_index}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-950/60">
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t('map_pollinators')}</p>
                    <p className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100 font-display">
                      {baseline.pollinator_abundance_index?.toFixed?.(3) ?? baseline.pollinator_abundance_index}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className="rounded-xl bg-emerald-500/5 p-3 border border-emerald-500/10 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            🌿 <strong>Gemelo Digital:</strong> La delimitación espacial consulta el modelo subrogado con resolución a nivel de parcela y hábitats contiguos.
          </div>
        </div>
      </div>
    </PanelCard>
  )
}
