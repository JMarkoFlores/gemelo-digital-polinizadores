import { useEffect, useRef, useState } from 'react'
import { FeatureGroup, MapContainer, TileLayer, useMap } from 'react-leaflet'
import { useTranslation } from 'react-i18next'
import 'leaflet-draw'
import L from '../lib/leaflet'
import PanelCard from './PanelCard'
import StatusBanner from './StatusBanner'

function DrawControl({ onChange }) {
  const map = useMap()
  const featureGroupRef = useRef(null)

  useEffect(() => {
    const featureGroup = new L.FeatureGroup()
    featureGroupRef.current = featureGroup
    map.addLayer(featureGroup)

    const drawControl = new L.Control.Draw({
      edit: { featureGroup },
      draw: {
        rectangle: true,
        polygon: true,
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

  return <FeatureGroup />
}

export default function MapSelectionCard({ geometry, onGeometryChange, baseline }) {
  const { t } = useTranslation()
  const [view, setView] = useState([-8.08, -78.85])

  useEffect(() => {
    if (baseline?.geometry?.coordinates?.[0]?.[0]) {
      const [lng, lat] = baseline.geometry.coordinates[0][0]
      setView([lat, lng])
    }
  }, [baseline])

  return (
    <PanelCard
      title={t('map_title')}
      subtitle={t('map_sub')}
    >
      <div className="grid gap-4 xl:grid-cols-[1.45fr_0.75fr]">
        <div className="h-[420px] overflow-hidden rounded-[1.5rem] border border-slate-200 dark:border-slate-800">
          <MapContainer center={view} zoom={11} scrollWheelZoom className="z-0">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <DrawControl onChange={onGeometryChange} />
          </MapContainer>
        </div>
        <div className="space-y-4">
          {geometry ? (
            <StatusBanner tone="success">{t('map_captured')}</StatusBanner>
          ) : (
            <StatusBanner>{t('map_drawPrompt')}</StatusBanner>
          )}
          <div className="rounded-[1.5rem] bg-slate-50 p-4 text-sm dark:bg-slate-950/50">
            <p className="font-medium">{t('map_currentGeoJson')}</p>
            <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-500 dark:text-slate-400">
              {geometry ? JSON.stringify(geometry, null, 2) : t('map_noGeom')}
            </pre>
          </div>
          {baseline ? (
            <div className="rounded-[1.5rem] border border-slate-200 p-4 text-sm dark:border-slate-800">
              <p className="font-medium">{t('map_baselineTitle')}</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-slate-500 dark:text-slate-400">{t('map_yield')}</p>
                  <p className="text-lg font-semibold">{baseline.crop_yield_index?.toFixed?.(3) ?? baseline.crop_yield_index}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">{t('map_pollinators')}</p>
                  <p className="text-lg font-semibold">{baseline.pollinator_abundance_index?.toFixed?.(3) ?? baseline.pollinator_abundance_index}</p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </PanelCard>
  )
}
