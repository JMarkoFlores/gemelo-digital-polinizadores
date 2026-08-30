import { useEffect, useState } from 'react'
import api from '../lib/api'
import EmptyState from '../components/EmptyState'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

export default function AdminSimulationsPage() {
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({ user_id: '', region: '' })
  const [error, setError] = useState('')

  const load = () => {
    const params = new URLSearchParams({ page: String(page), page_size: '8' })
    if (filters.user_id) params.append('user_id', filters.user_id)
    if (filters.region) params.append('region', filters.region)
    api
      .get(`/api/admin/simulations?${params.toString()}`)
      .then((response) => {
        setItems(response.data.items)
        setTotal(response.data.total)
      })
      .catch((requestError) => setError(requestError.response?.data?.detail || 'No fue posible cargar simulaciones globales.'))
  }

  useEffect(() => {
    load()
  }, [page])

  const exportWord = async (simulationId) => {
    const response = await api.get(`/api/admin/simulations/${simulationId}/report`)
    const { exportSimulationReportToDocx } = await import('../lib/exporters')
    await exportSimulationReportToDocx(response.data)
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">Admin</p>
        <h1 className="mt-3 text-4xl font-semibold">Trazabilidad y reportes</h1>
      </section>
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      <PanelCard title="Filtros globales" subtitle="La tabla usa paginacion del backend y filtros por usuario y region.">
        <div className="grid gap-3 md:grid-cols-[0.4fr_0.6fr_auto]">
          <input value={filters.user_id} onChange={(e) => setFilters((prev) => ({ ...prev, user_id: e.target.value }))} placeholder="Usuario ID" className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
          <input value={filters.region} onChange={(e) => setFilters((prev) => ({ ...prev, region: e.target.value }))} placeholder="Region" className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
          <button onClick={() => { setPage(1); load() }} className="rounded-2xl bg-primary-600 px-4 py-3 text-sm text-white">Aplicar</button>
        </div>
      </PanelCard>
      <PanelCard title="Simulaciones de la plataforma" subtitle="Exporta cada registro a PDF o solicita al backend los datos completos para Word.">
        {items.length === 0 ? (
          <EmptyState title="Sin resultados" description="No hay simulaciones que coincidan con los filtros actuales." />
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.id} className="flex flex-col gap-4 rounded-[1.5rem] border border-slate-200 p-4 dark:border-slate-800 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <p className="font-medium">Simulacion #{item.id}</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Usuario {item.usuario_id} | {new Date(item.fecha).toLocaleString()}</p>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Region: {item.metricas_base?.region_label || 'N/A'} | Rendimiento optimo: {item.metricas_optimas?.crop_yield_index ?? item.metricas_optimas?.rendimiento ?? 'N/A'}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={async () => {
                      const { exportSimulationToPdf } = await import('../lib/exporters')
                      exportSimulationToPdf(item)
                    }}
                    className="rounded-2xl bg-slate-200 px-4 py-2 text-sm dark:bg-slate-800"
                  >
                    PDF
                  </button>
                  <button onClick={() => exportWord(item.id)} className="rounded-2xl bg-primary-600 px-4 py-2 text-sm text-white">Word</button>
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between pt-2 text-sm">
              <span className="text-slate-500 dark:text-slate-400">{total} registros</span>
              <div className="flex gap-2">
                <button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">Anterior</button>
                <button onClick={() => setPage((value) => value + 1)} disabled={page * 8 >= total} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">Siguiente</button>
              </div>
            </div>
          </div>
        )}
      </PanelCard>
    </div>
  )
}
