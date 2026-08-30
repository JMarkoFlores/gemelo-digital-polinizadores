import { useEffect } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from '../lib/leaflet'
import { useTranslation } from 'react-i18next'
import PanelCard from './PanelCard'

/* ── Auto-fit the map to a GeoJSON layer's bounds ─────────────────────── */
function FitBounds({ data }) {
  const map = useMap()
  useEffect(() => {
    if (!data) return
    try {
      const layer = L.geoJSON(data)
      const bounds = layer.getBounds()
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [16, 16] })
    } catch {
      // ignore malformed geometries
    }
  }, [map, data])
  return null
}

/* ── Color style for optimized FeatureCollection ──────────────────────── */
function optimizedStyle(feature) {
  const color = feature?.properties?.color ?? '#60a5fa'
  return { color, fillColor: color, fillOpacity: 0.55, weight: 2 }
}

function onEachOptimized(feature, layer) {
  if (feature?.properties?.label) {
    layer.bindTooltip(feature.properties.label, { sticky: true, className: 'leaflet-tooltip-dark' })
  }
}

const TILE = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'

const LEGEND = [
  { color: '#86efac', label: 'Cultivo' },
  { color: '#15803d', label: 'Seminatural' },
  { color: '#fbbf24', label: 'Franjas florales' },
]

/* ── Derive a safe center from any GeoJSON ────────────────────────────── */
function centerOf(geojson) {
  try {
    const layer = L.geoJSON(geojson)
    const bounds = layer.getBounds()
    if (bounds.isValid()) {
      const c = bounds.getCenter()
      return [c.lat, c.lng]
    }
  } catch {
    // fallback
  }
  return [-8.08, -78.85]
}

/* ── Main component ───────────────────────────────────────────────────── */
export default function ComparisonMapsCard({ baselineGeometry, optimizedGeojson }) {
  const { t } = useTranslation()

  if (!baselineGeometry || !optimizedGeojson) return null

  const baselineFeature = {
    type: 'Feature',
    geometry: baselineGeometry,
    properties: { label: t('results_baseLandscape') },
  }

  const center = centerOf(baselineFeature)

  return (
    <PanelCard
      title={t('results_spatial_title')}
      subtitle={t('results_spatial_sub')}
    >
      <div className="grid gap-6 xl:grid-cols-2">

        {/* ── Map 1: Original baseline polygon ── */}
        <div className="space-y-2">
          <p className="text-sm font-semibold">{t('results_baseLandscape')}</p>
          <div className="h-72 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
            <MapContainer
              center={center}
              zoom={11}
              scrollWheelZoom={false}
              className="h-full w-full z-0"
              key={JSON.stringify(center) + '-base'}
            >
              <TileLayer attribution={TILE_ATTR} url={TILE} />
              <FitBounds data={baselineFeature} />
              <GeoJSON
                data={baselineFeature}
                style={{ color: '#3b82f6', fillColor: '#93c5fd', fillOpacity: 0.35, weight: 2.5 }}
              />
            </MapContainer>
          </div>
          <p className="text-center text-xs text-slate-400 dark:text-slate-500">
            {t('results_baseLandscape')} — {t('results_crop')}: {baselineGeometry ? '—' : 'N/A'}
          </p>
        </div>

        {/* ── Map 2: Optimized FeatureCollection ── */}
        <div className="space-y-2">
          <p className="text-sm font-semibold">{t('results_optLandscape')}</p>
          <div className="h-72 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
            <MapContainer
              center={center}
              zoom={11}
              scrollWheelZoom={false}
              className="h-full w-full z-0"
              key={JSON.stringify(center) + '-opt'}
            >
              <TileLayer attribution={TILE_ATTR} url={TILE} />
              <FitBounds data={optimizedGeojson} />
              <GeoJSON
                data={optimizedGeojson}
                style={optimizedStyle}
                onEachFeature={onEachOptimized}
              />
            </MapContainer>
          </div>

          {/* ── Legend ── */}
          <div className="flex flex-wrap justify-center gap-4 text-xs">
            {LEGEND.map(({ color, label }) => (
              <span key={label} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-3 w-3 flex-shrink-0 rounded-sm border border-black/10"
                  style={{ background: color }}
                />
                <span className="text-slate-600 dark:text-slate-300">{label}</span>
              </span>
            ))}
          </div>
        </div>

      </div>
    </PanelCard>
  )
}
