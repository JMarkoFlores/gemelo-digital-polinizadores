import { useState, useEffect, useMemo, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import { MapContainer, TileLayer, GeoJSON, Polygon, Tooltip, useMap } from 'react-leaflet'
import L from '../lib/leaflet'
import 'leaflet/dist/leaflet.css'
import { generateLandscapeGrid } from './LandscapeDiorama3D'
import { LAND_USE_PALETTE } from '../lib/landUseColors'
import { LandUseProgressBar, LandUse2DCards } from './LandUseDistributionCards'

// Sutherland-Hodgman Polygon Clipping against bounding rectangle
function clipPolygonAgainstRectangle(subjectPoly, rect) {
  // rect: [minX, minY, maxX, maxY]
  let outputList = subjectPoly

  // Clip against left edge (x >= minX)
  outputList = clipAgainstEdge(outputList, rect[0], null, true)
  // Clip against right edge (x <= maxX)
  outputList = clipAgainstEdge(outputList, rect[2], null, false)
  // Clip against bottom edge (y >= minY)
  outputList = clipAgainstEdge(outputList, null, rect[1], true)
  // Clip against top edge (y <= maxY)
  outputList = clipAgainstEdge(outputList, null, rect[3], false)

  return outputList
}

function clipAgainstEdge(pts, edgeX, edgeY, isGreater) {
  if (!pts || pts.length === 0) return []
  const output = []
  let prev = pts[pts.length - 1]

  for (let i = 0; i < pts.length; i++) {
    let curr = pts[i]
    let prevInside =
      edgeX !== null
        ? isGreater
          ? prev[0] >= edgeX
          : prev[0] <= edgeX
        : isGreater
          ? prev[1] >= edgeY
          : prev[1] <= edgeY

    let currInside =
      edgeX !== null
        ? isGreater
          ? curr[0] >= edgeX
          : curr[0] <= edgeX
        : isGreater
          ? curr[1] >= edgeY
          : curr[1] <= edgeY

    if (currInside) {
      if (!prevInside) {
        output.push(computeIntersection(prev, curr, edgeX, edgeY))
      }
      output.push(curr)
    } else if (prevInside) {
      output.push(computeIntersection(prev, curr, edgeX, edgeY))
    }
    prev = curr
  }
  return output
}

function computeIntersection(p1, p2, edgeX, edgeY) {
  if (edgeX !== null) {
    let slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
    return [edgeX, p1[1] + slope * (edgeX - p1[0])]
  } else {
    let slope = (p2[0] - p1[0]) / (p2[1] - p1[1])
    return [p1[0] + slope * (edgeY - p1[1]), edgeY]
  }
}

/**
 * Leaflet helper to invalidate map container size and auto-fit polygon bounds.
 * Uses bounds.pad(0.14) to maintain an optimal 14% margin around small and large polygons.
 */
function MapAutoFitHelper({ geometry, center, triggerCount = 0 }) {
  const map = useMap()

  useEffect(() => {
    const fit = () => {
      try {
        map.invalidateSize()
        const coords = geometry?.coordinates?.[0]
        if (coords && coords.length > 2) {
          const latLngs = coords.map(([lon, lat]) => [lat, lon])
          const bounds = L.latLngBounds(latLngs)
          if (bounds.isValid()) {
            // Margen proporcional razonable (~14%) para encuadre nítido en tarjetas compactas y modales
            const paddedBounds = bounds.pad(0.14)
            map.fitBounds(paddedBounds, { padding: [10, 10], maxZoom: 18, animate: false })
            return
          }
        }
        if (center) {
          map.setView(center, 14, { animate: false })
        }
      } catch {
        if (center) map.setView(center, 14, { animate: false })
      }
    }

    fit()
    const timer1 = setTimeout(fit, 80)
    const timer2 = setTimeout(fit, 250)

    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
    }
  }, [map, geometry, center, triggerCount])

  return null
}

export default function ExpandableMapCard({
  title,
  subtitle,
  mix,
  geometry,
  center,
  optimal,
  elevationData = null,
}) {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const [fitTrigger, setFitTrigger] = useState(0)
  const [showHillshade, setShowHillshade] = useState(true)

  const mapStyle = optimal
    ? { fillColor: '#10b981', fillOpacity: 0.55, color: '#f59e0b', weight: 3 }
    : { fillColor: '#64748b', fillOpacity: 0.25, color: '#94a3b8', weight: 2 }

  const cropPct = Number(mix?.crop_area_pct ?? 0)
  const naturalPct = Number(mix?.natural_area_pct ?? 0)
  const floralPct = Number(mix?.floral_strips_pct ?? 0)
  const totalPct = cropPct + naturalPct + floralPct

  // Extract outer ring of geometry to use for clipping
  const { subjectPoly, minLon, minLat, maxLon, maxLat } = useMemo(() => {
    let poly = []
    let minX = 999
    let minY = 999
    let maxX = -999
    let maxY = -999
    if (geometry?.coordinates?.[0]) {
      poly = geometry.coordinates[0]
      poly.forEach(([lon, lat]) => {
        if (lon < minX) minX = lon
        if (lon > maxX) maxX = lon
        if (lat < minY) minY = lat
        if (lat > maxY) maxY = lat
      })
    }
    return { subjectPoly: poly, minLon: minX, minLat: minY, maxLon: maxX, maxLat: maxY }
  }, [geometry])

  // Generate deterministic grid (seed 84 for optimal, 42 for base) with elevation relief data
  const seed = optimal ? 84 : 42
  const cells = useMemo(
    () => generateLandscapeGrid(mix, seed, elevationData),
    [mix, seed, elevationData]
  )

  // Compute clipped land-use polygon features with topography hillshade
  const gridPolygonFeatures = useMemo(() => {
    if (subjectPoly.length <= 2 || minLon === 999) return []
    const cellWidth = (maxLon - minLon) / 10
    const cellHeight = (maxLat - minLat) / 10
    const features = []

    const hasElevation = !!(elevationData?.available && elevationData?.matrix)
    const matrix = elevationData?.matrix
    const rangeM = Number(elevationData?.elevation_range_m ?? 0)
    const minE = Number(elevationData?.min_elevation_m ?? 0)

    cells.forEach((cell) => {
      const rectMinLon = minLon + cell.x * cellWidth
      const rectMaxLon = rectMinLon + cellWidth
      const rectMaxLat = maxLat - cell.z * cellHeight
      const rectMinLat = rectMaxLat - cellHeight

      const rect = [rectMinLon, rectMinLat, rectMaxLon, rectMaxLat]
      const clipped = clipPolygonAgainstRectangle(subjectPoly, rect)

      if (clipped && clipped.length > 2) {
        let baseColor = 'transparent'
        let typeLabel = 'Área sin modelar'
        if (cell.type === 'crop') {
          baseColor = LAND_USE_PALETTE.crop.hex // Cultivo verde intenso (#059669)
          typeLabel = 'Cultivo'
        } else if (cell.type === 'natural') {
          baseColor = LAND_USE_PALETTE.natural.hex // Seminatural azul claro (#38bdf8 / #7EC8E3)
          typeLabel = 'Seminatural'
        } else if (cell.type === 'floral') {
          baseColor = LAND_USE_PALETTE.floral.hex // Franjas florales naranja (#f59e0b)
          typeLabel = 'Franjas Florales'
        }

        if (baseColor !== 'transparent') {
          let elevM = null
          let relElevM = null
          let fillOpacity = 0.65
          let strokeColor = baseColor
          let strokeWeight = 1

          if (hasElevation && matrix) {
            const z = cell.z
            const x = cell.x
            elevM = matrix[z]?.[x] ?? null
            if (elevM !== null) {
              relElevM = elevM - minE

              if (rangeM >= 4.0) {
                const left = matrix[z]?.[Math.max(0, x - 1)] ?? elevM
                const right = matrix[z]?.[Math.min(9, x + 1)] ?? elevM
                const top = matrix[Math.max(0, z - 1)]?.[x] ?? elevM
                const bottom = matrix[Math.min(9, z + 1)]?.[x] ?? elevM

                // Hillshade relief lighting from North-West
                const slopeNW = ((top - elevM) + (left - elevM)) / 2.0
                const normSlope = Math.max(-0.25, Math.min(0.25, slopeNW / Math.max(12.0, rangeM * 0.22)))

                // Modulate fillOpacity according to sun incidence
                fillOpacity = Math.max(0.42, Math.min(0.85, 0.65 + normSlope * 0.45))
                if (normSlope > 0.08) {
                  strokeColor = '#ffffff'
                  strokeWeight = 1.2
                } else if (normSlope < -0.08) {
                  strokeColor = '#0f172a'
                  strokeWeight = 1.2
                }
              }
            }
          }

          features.push({
            id: `${cell.x}-${cell.z}`,
            positions: clipped.map(([lon, lat]) => [lat, lon]),
            color: baseColor,
            fillOpacity,
            strokeColor,
            strokeWeight,
            typeLabel,
            elevationM: elevM,
            relElevationM: relElevM,
          })
        }
      }
    })
    return features
  }, [cells, subjectPoly, minLon, minLat, maxLon, maxLat, elevationData])

  // Manage body scroll and Escape key when modal is open
  useEffect(() => {
    if (!isExpanded) return

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsExpanded(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isExpanded])

  const handleRecenter = useCallback(() => {
    setFitTrigger((prev) => prev + 1)
  }, [])

  const hasElevation = !!(elevationData?.available && elevationData?.elevation_range_m !== undefined)
  const rangeM = Number(elevationData?.elevation_range_m ?? 0)

  return (
    <>
      {/* Standard 2D Leaflet Card in Dashboard */}
      <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/90 dark:bg-slate-900/90 transition-all hover:border-slate-300 dark:hover:border-slate-700">
        <div>
          {/* Card Header with Badges & Expand Action */}
          <div className="mb-3 flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-bold text-slate-900 dark:text-slate-100 font-display text-base truncate">
                  {title}
                </h3>
                {optimal ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Recomendación IA
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                    Estado Actual
                  </span>
                )}

                {hasElevation ? (
                  <span
                    className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2 py-0.5 text-[11px] font-semibold text-sky-700 dark:text-sky-300"
                    title={`Desnivel topográfico real: ${rangeM.toFixed(0)} m`}
                  >
                    🏔️ {rangeM > 4 ? `Relieve (Δ ${rangeM.toFixed(0)}m)` : 'Terreno Llano'}
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400">
                    🏔️ Vista plana
                  </span>
                )}
              </div>
              {subtitle && (
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
                  {subtitle}
                </p>
              )}
            </div>

            {/* Actions: Toggle Hillshade & Expand */}
            <div className="flex items-center gap-1.5 shrink-0">
              {hasElevation && rangeM >= 4 && (
                <button
                  type="button"
                  onClick={() => setShowHillshade(!showHillshade)}
                  className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[11px] font-medium transition-all ${
                    showHillshade
                      ? 'border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950/60 dark:text-sky-300'
                      : 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                  }`}
                  title={showHillshade ? 'Desactivar sombreado de relieve' : 'Activar sombreado de relieve topográfico'}
                >
                  🏔️ Relieve
                </button>
              )}

              <button
                type="button"
                onClick={() => setIsExpanded(true)}
                className="inline-flex items-center gap-1.5 shrink-0 rounded-lg border border-slate-200 bg-slate-50/80 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-emerald-500/40 hover:bg-white hover:text-emerald-600 hover:shadow-xs dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-200 dark:hover:border-emerald-500/50 dark:hover:bg-slate-800 dark:hover:text-emerald-400 transition-all cursor-pointer"
                title="Ampliar vista del mapa satelital en modal"
                aria-label={`Ampliar vista de ${title}`}
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                  />
                </svg>
                <span>Ampliar</span>
              </button>
            </div>
          </div>

          {/* Compact Satellite Map */}
          <div className="group relative z-0 h-60 w-full overflow-hidden rounded-xl border border-slate-200/80 dark:border-slate-800">
            {center && (
              <MapContainer
                center={center}
                zoom={14}
                zoomControl={false}
                dragging={false}
                scrollWheelZoom={false}
                className="h-full w-full"
              >
                <TileLayer
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  attribution="Tiles &copy; Esri"
                />
                {geometry && (
                  <GeoJSON
                    data={geometry}
                    pathOptions={{ ...mapStyle, fillOpacity: 0.1 }}
                  />
                )}
                {gridPolygonFeatures.map((p) => (
                  <Polygon
                    key={p.id}
                    positions={p.positions}
                    pathOptions={{
                      fillColor: p.color,
                      fillOpacity: showHillshade ? p.fillOpacity : 0.65,
                      color: showHillshade ? p.strokeColor : p.color,
                      weight: showHillshade ? p.strokeWeight : 1,
                      opacity: 0.85,
                    }}
                  >
                    <Tooltip sticky direction="top" className="text-xs">
                      <div className="font-sans">
                        <span className="font-bold">{p.typeLabel}</span>
                        {p.elevationM !== null && p.elevationM !== undefined && (
                          <div className="text-[11px] text-slate-300 mt-0.5 font-mono">
                            🏔️ Cota: <strong>{p.elevationM.toFixed(0)} m</strong>
                            {p.relElevationM !== null && ` (+${p.relElevationM.toFixed(0)}m)`}
                          </div>
                        )}
                      </div>
                    </Tooltip>
                  </Polygon>
                ))}
                <MapAutoFitHelper geometry={geometry} center={center} />
              </MapContainer>
            )}

            {/* Subtle Hover Action overlay to quickly open */}
            <div
              onClick={() => setIsExpanded(true)}
              className="absolute inset-0 bg-black/0 group-hover:bg-black/15 transition-all flex items-center justify-center cursor-pointer pointer-events-auto"
              title="Haz clic para ampliar la vista del mapa"
            >
              <span className="opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900/80 text-white text-xs font-semibold px-3 py-1.5 rounded-lg backdrop-blur-xs flex items-center gap-1.5 shadow-md">
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
                  />
                </svg>
                Ampliar mapa
              </span>
            </div>

            <div className="pointer-events-none absolute bottom-2 right-2 rounded-md bg-black/60 px-2 py-0.5 text-[10px] text-white/90 backdrop-blur-xs font-mono">
              Esri World Imagery
            </div>
          </div>

          {/* Proportional Land-Use Progress Bar & Redesigned 2D Cards (Mockup 1) */}
          <div className="mt-4 space-y-3">
            <LandUseProgressBar
              cropPct={cropPct}
              naturalPct={naturalPct}
              floralPct={floralPct}
              title="Distribución de Superficie"
              totalLabel={`${totalPct.toFixed(1)}% Total`}
            />
            <LandUse2DCards mix={mix} />
          </div>
        </div>
      </div>

      {/* Expanded Modal View rendered via Portal */}
      {isExpanded &&
        createPortal(
          <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 md:p-8 animate-in fade-in duration-200">
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm transition-opacity"
              onClick={() => setIsExpanded(false)}
            />

            {/* Modal Dialog Card */}
            <div
              className="relative z-10 flex flex-col w-full max-w-6xl max-h-[92vh] overflow-hidden rounded-2xl sm:rounded-3xl border border-slate-200/90 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Top Bar */}
              <div className="flex items-center justify-between border-b border-slate-200/80 px-5 py-4 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                      />
                    </svg>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
                        {title}
                      </h2>
                      {optimal ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          Recomendación IA
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          Estado Actual
                        </span>
                      )}

                      {hasElevation && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2 py-0.5 text-xs font-semibold text-sky-700 dark:text-sky-300">
                          🏔️ {rangeM > 4 ? `Relieve Real: ${elevationData.min_elevation_m}m - ${elevationData.max_elevation_m}m (Δ ${rangeM.toFixed(0)}m)` : 'Terreno Llano'}
                        </span>
                      )}
                    </div>
                    {subtitle && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
                    )}
                  </div>
                </div>

                {/* Modal Top Actions */}
                <div className="flex items-center gap-2">
                  {hasElevation && rangeM >= 4 && (
                    <button
                      type="button"
                      onClick={() => setShowHillshade(!showHillshade)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                        showHillshade
                          ? 'border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950/60 dark:text-sky-300'
                          : 'border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                      }`}
                    >
                      🏔️ Sombreado de Relieve: {showHillshade ? 'ON' : 'OFF'}
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={handleRecenter}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-2xs hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 transition-colors"
                    title="Reajustar y centrar la vista al polígono seleccionado"
                  >
                    <svg
                      className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
                      />
                    </svg>
                    <span>Reajustar vista</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsExpanded(false)}
                    className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors dark:hover:bg-slate-800 dark:hover:text-slate-200"
                    title="Cerrar modal (Esc)"
                    aria-label="Cerrar modal"
                  >
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Large Interactive Leaflet Map */}
              <div className="relative h-[55vh] sm:h-[62vh] md:h-[66vh] w-full bg-slate-950">
                {center && (
                  <MapContainer
                    center={center}
                    zoom={14}
                    zoomControl={true}
                    dragging={true}
                    scrollWheelZoom={true}
                    doubleClickZoom={true}
                    className="h-full w-full"
                  >
                    <TileLayer
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                      attribution="Tiles &copy; Esri"
                    />
                    {geometry && (
                      <GeoJSON
                        data={geometry}
                        pathOptions={{ ...mapStyle, fillOpacity: 0.1 }}
                      />
                    )}
                    {gridPolygonFeatures.map((p) => (
                      <Polygon
                        key={`expanded-${p.id}`}
                        positions={p.positions}
                        pathOptions={{
                          fillColor: p.color,
                          fillOpacity: showHillshade ? p.fillOpacity : 0.65,
                          color: showHillshade ? p.strokeColor : p.color,
                          weight: showHillshade ? p.strokeWeight : 1,
                          opacity: 0.85,
                        }}
                      >
                        <Tooltip sticky direction="top" className="text-xs">
                          <div className="font-sans">
                            <span className="font-bold">{p.typeLabel}</span>
                            {p.elevationM !== null && p.elevationM !== undefined && (
                              <div className="text-[11px] text-slate-300 mt-0.5 font-mono">
                                🏔️ Cota: <strong>{p.elevationM.toFixed(0)} m s.n.m.</strong>
                                {p.relElevationM !== null && ` (+${p.relElevationM.toFixed(0)}m)`}
                              </div>
                            )}
                          </div>
                        </Tooltip>
                      </Polygon>
                    ))}
                    <MapAutoFitHelper
                      geometry={geometry}
                      center={center}
                      triggerCount={fitTrigger}
                    />
                  </MapContainer>
                )}

                {/* Floating Navigation Tip */}
                <div className="pointer-events-none absolute top-3 right-3 z-[1000] hidden sm:flex items-center gap-1.5 rounded-lg bg-slate-900/80 px-3 py-1 text-xs text-slate-200 shadow-md backdrop-blur-xs border border-slate-700/60 font-medium">
                  <span>💡 Arrastra el mapa o usa la rueda del ratón para zoom detallado</span>
                </div>

                <div className="pointer-events-none absolute bottom-3 right-3 z-[1000] rounded-md bg-black/60 px-2.5 py-1 text-[11px] text-white/90 backdrop-blur-xs font-mono">
                  Esri World Imagery • Topografía Satelital
                </div>
              </div>

              {/* Modal Bottom Footer Info */}
              <div className="border-t border-slate-200/80 px-6 py-4 dark:border-slate-800 bg-white dark:bg-slate-900">
                <div className="space-y-3">
                  <LandUseProgressBar
                    cropPct={cropPct}
                    naturalPct={naturalPct}
                    floralPct={floralPct}
                    title="Distribución Espacial en Grilla 10×10 (1 celda = 1% del área)"
                    totalLabel={`${totalPct.toFixed(1)}% modelado`}
                  />
                  <LandUse2DCards mix={mix} />
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  )
}
