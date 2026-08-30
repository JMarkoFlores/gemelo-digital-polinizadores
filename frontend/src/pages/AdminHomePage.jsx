import { useEffect, useState } from 'react'
import api from '../lib/api'
import MetricCard from '../components/MetricCard'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

export default function AdminHomePage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/admin/dashboard').then((response) => setData(response.data)).catch((requestError) => setError(requestError.response?.data?.detail || 'No fue posible cargar el panel admin.'))
  }, [])

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">Admin</p>
        <h1 className="mt-3 text-4xl font-semibold">Centro de control de la plataforma</h1>
      </section>
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Usuarios totales" value={data?.total_users ?? '...'} hint="Conteo global de cuentas creadas." />
        <MetricCard label="Usuarios activos" value={data?.active_users ?? '...'} hint="Accesos habilitados actualmente." />
        <MetricCard label="Simulaciones del mes" value={data?.simulations_this_month ?? '...'} hint="Trazabilidad reciente de uso." />
      </div>
      <PanelCard title="Zonas mas simuladas" subtitle="Resumen agregado por region derivada del centroide de la geometria.">
        <div className="grid gap-3 md:grid-cols-2">
          {(data?.top_regions || []).map((region) => (
            <div key={region.region} className="rounded-2xl bg-slate-50 px-4 py-4 dark:bg-slate-950/50">
              <p className="font-medium">{region.region}</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{region.count} simulaciones</p>
            </div>
          ))}
        </div>
      </PanelCard>
    </div>
  )
}
