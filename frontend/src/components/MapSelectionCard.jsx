import { useEffect, useRef, useState } from 'react'
import { FeatureGroup, MapContainer, TileLayer, useMap } from 'react-leaflet'
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
  const [view, setView] = useState([-8.08, -78.85])

  useEffect(() => {
    if (baseline?.geometry?.coordinates?.[0]?.[0]) {
      const [lng, lat] = baseline.geometry.coordinates[0][0]
      setView([lat, lng])
    }
  }, [baseline])

  return (
    <PanelCard
      title="Seleccion del area"
      subtitle="Dibuja un poligono o rectangulo sobre el valle de interes. El frontend captura el GeoJSON real y lo usa para optimizar."
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
            <StatusBanner tone="success">Area capturada correctamente. Ya puedes configurar el escenario y lanzar la optimizacion.</StatusBanner>
          ) : (
            <StatusBanner>Dibuja un poligono o rectangulo para activar la simulacion.</StatusBanner>
          )}
          <div className="rounded-[1.5rem] bg-slate-50 p-4 text-sm dark:bg-slate-950/50">
            <p className="font-medium">GeoJSON actual</p>
            <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-500 dark:text-slate-400">
              {geometry ? JSON.stringify(geometry, null, 2) : 'Sin geometria seleccionada'}
            </pre>
          </div>
          {baseline ? (
            <div className="rounded-[1.5rem] border border-slate-200 p-4 text-sm dark:border-slate-800">
              <p className="font-medium">Linea base calculada</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Rendimiento</p>
                  <p className="text-lg font-semibold">{baseline.crop_yield_index?.toFixed?.(3) ?? baseline.crop_yield_index}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Polinizadores</p>
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
