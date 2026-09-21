import { useState, useEffect, useMemo, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import { MapContainer, TileLayer, GeoJSON, Polygon, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { generateLandscapeGrid } from './LandscapeDiorama3D'

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
 * Prevents grey tiles and layout mismatch when expanding into modal dialogs.
 */
function MapAutoFitHelper({ geometry, center, triggerCount = 0 }) {
  const map = useMap()

  useEffect(() => {
    // Initial invalidate
    map.invalidateSize()

    // Delayed invalidate to accommodate modal opening / animation
    const timer = setTimeout(() => {
      map.invalidateSize()
      if (geometry?.coordinates?.[0]?.length) {
        try {
          const coords = geometry.coordinates[0]
          const bounds = coords.map(([lon, lat]) => [lat, lon])
          map.fitBounds(bounds, { padding: [35, 35], maxZoom: 17 })
        } catch {
          if (center) map.setView(center, 14)
        }
      } else if (center) {
        map.setView(center, 14)
      }
    }, 120)

    return () => clearTimeout(timer)
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
}) {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const [fitTrigger, setFitTrigger] = useState(0)

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

  // Generate deterministic grid (seed 84 for optimal, 42 for base)
  const seed = optimal ? 84 : 42
  const cells = useMemo(() => generateLandscapeGrid(mix, seed), [mix, seed])

  // Compute clipped land-use polygon features
  const gridPolygonFeatures = useMemo(() => {
    if (subjectPoly.length <= 2 || minLon === 999) return []
    const cellWidth = (maxLon - minLon) / 10
    const cellHeight = (maxLat - minLat) / 10
    const features = []

    cells.forEach((cell) => {
      const rectMinLon = minLon + cell.x * cellWidth
      const rectMaxLon = rectMinLon + cellWidth
      const rectMaxLat = maxLat - cell.z * cellHeight
      const rectMinLat = rectMaxLat - cellHeight

      const rect = [rectMinLon, rectMinLat, rectMaxLon, rectMaxLat]
      const clipped = clipPolygonAgainstRectangle(subjectPoly, rect)

      if (clipped && clipped.length > 2) {
        let color = 'transparent'
        if (cell.type === 'crop') color = '#059669' // emerald-600
        else if (cell.type === 'natural') color = '#065f46' // emerald-800
        else if (cell.type === 'floral') color = '#f59e0b' // amber-500

        if (color !== 'transparent') {
          features.push({
            id: `${cell.x}-${cell.z}`,
            positions: clipped.map(([lon, lat]) => [lat, lon]),
            color,
          })
        }
      }
    })
    return features
  }, [cells, subjectPoly, minLon, minLat, maxLon, maxLat])

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
              </div>
              {subtitle && (
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
                  {subtitle}
                </p>
              )}
            </div>

            {/* Individual Expand / Zoom Button */}
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
                      fillOpacity: 0.65,
                      color: p.color,
                      weight: 1,
                      opacity: 0.8,
                    }}
                  />
                ))}
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

          {/* Proportional Land-Use Bar */}
          <div className="mt-4 space-y-1.5">
            <div className="flex justify-between text-xs font-medium text-slate-600 dark:text-slate-300">
              <span>Distribución de Superficie</span>
              <span className="font-mono text-slate-400">{totalPct.toFixed(1)}% Total</span>
            </div>
            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                style={{ width: `${cropPct}%` }}
                className="bg-emerald-500 transition-all"
                title={`Cultivo: ${cropPct.toFixed(1)}%`}
              />
              <div
                style={{ width: `${naturalPct}%` }}
                className="bg-sky-500 transition-all"
                title={`Seminatural: ${naturalPct.toFixed(1)}%`}
              />
              <div
                style={{ width: `${floralPct}%` }}
                className="bg-amber-400 transition-all"
                title={`Franjas: ${floralPct.toFixed(1)}%`}
              />
            </div>
          </div>

          {/* Breakdown Metric Chips (acts as Legend) */}
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-2.5 dark:bg-emerald-500/[0.08]">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <span className="h-2 w-2 rounded-xs bg-[#059669] inline-block shadow-xs" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                  {t('results_crop')}
                </p>
              </div>
              <p className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
                {mix?.crop_area_pct?.toFixed?.(1) ?? 'N/A'}%
              </p>
            </div>
            <div className="rounded-xl border border-sky-500/20 bg-sky-500/[0.04] p-2.5 dark:bg-sky-500/[0.08]">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <span className="h-2 w-2 rounded-xs bg-[#065f46] inline-block shadow-xs" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300">
                  {t('results_seminatural')}
                </p>
              </div>
              <p className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
                {mix?.natural_area_pct?.toFixed?.(1) ?? 'N/A'}%
              </p>
            </div>
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-2.5 dark:bg-amber-500/[0.08]">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <span className="h-2 w-2 rounded-xs bg-[#f59e0b] inline-block shadow-xs" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                  {t('results_floralStrips')}
                </p>
              </div>
              <p className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
                {mix?.floral_strips_pct?.toFixed?.(1) ?? 'N/A'}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Modal / Lightbox Dialog */}
      {isExpanded &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={`modal-title-${optimal ? 'opt' : 'base'}`}
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-3 sm:p-6 animate-fadeIn"
            onClick={(e) => {
              if (e.target === e.currentTarget) setIsExpanded(false)
            }}
          >
            <div className="relative flex flex-col w-full max-w-5xl max-h-[94vh] rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
              {/* Modal Header */}
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3
                        id={`modal-title-${optimal ? 'opt' : 'base'}`}
                        className="font-bold text-slate-900 dark:text-slate-100 font-display text-lg"
                      >
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
                    </div>
                    {subtitle && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
                    )}
                  </div>
                </div>

                {/* Modal Top Actions */}
                <div className="flex items-center gap-2">
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
                          fillOpacity: 0.65,
                          color: p.color,
                          weight: 1,
                          opacity: 0.8,
                        }}
                      />
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

                <div className="pointer-events-none absolute bottom-2 right-2 z-[1000] rounded-md bg-black/60 px-2.5 py-0.5 text-[11px] text-white/90 backdrop-blur-xs font-mono">
                  Esri World Imagery
                </div>
              </div>

              {/* Modal Footer with Proportional Bar & Legend Chips */}
              <div className="border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                <div className="grid gap-4 md:grid-cols-2 items-center">
                  {/* Proportional Land-Use Bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-medium text-slate-600 dark:text-slate-300">
                      <span>Distribución Proporcional de Superficie</span>
                      <span className="font-mono text-slate-400">{totalPct.toFixed(1)}% Total</span>
                    </div>
                    <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        style={{ width: `${cropPct}%` }}
                        className="bg-emerald-500 transition-all"
                        title={`Cultivo: ${cropPct.toFixed(1)}%`}
                      />
                      <div
                        style={{ width: `${naturalPct}%` }}
                        className="bg-sky-500 transition-all"
                        title={`Seminatural: ${naturalPct.toFixed(1)}%`}
                      />
                      <div
                        style={{ width: `${floralPct}%` }}
                        className="bg-amber-400 transition-all"
                        title={`Franjas Florales: ${floralPct.toFixed(1)}%`}
                      />
                    </div>
                  </div>

                  {/* Breakdown Chips */}
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-2 dark:bg-emerald-500/[0.08]">
                      <div className="flex items-center justify-center gap-1.5 mb-0.5">
                        <span className="h-2 w-2 rounded-xs bg-[#059669] inline-block shadow-xs" />
                        <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                          {t('results_crop')}
                        </p>
                      </div>
                      <p className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">
                        {mix?.crop_area_pct?.toFixed?.(1) ?? 'N/A'}%
                      </p>
                    </div>

                    <div className="rounded-xl border border-sky-500/20 bg-sky-500/[0.04] p-2 dark:bg-sky-500/[0.08]">
                      <div className="flex items-center justify-center gap-1.5 mb-0.5">
                        <span className="h-2 w-2 rounded-xs bg-[#065f46] inline-block shadow-xs" />
                        <p className="text-[10px] font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300">
                          {t('results_seminatural')}
                        </p>
                      </div>
                      <p className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">
                        {mix?.natural_area_pct?.toFixed?.(1) ?? 'N/A'}%
                      </p>
                    </div>

                    <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-2 dark:bg-amber-500/[0.08]">
                      <div className="flex items-center justify-center gap-1.5 mb-0.5">
                        <span className="h-2 w-2 rounded-xs bg-[#f59e0b] inline-block shadow-xs" />
                        <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                          {t('results_floralStrips')}
                        </p>
                      </div>
                      <p className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">
                        {mix?.floral_strips_pct?.toFixed?.(1) ?? 'N/A'}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  )
}
