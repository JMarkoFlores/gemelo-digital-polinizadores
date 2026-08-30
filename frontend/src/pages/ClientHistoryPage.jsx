import { useEffect, useState } from 'react'
import api from '../lib/api'
import PanelCard from '../components/PanelCard'
import SimulationHistoryList from '../components/SimulationHistoryList'
import StatusBanner from '../components/StatusBanner'

export default function ClientHistoryPage() {
  const [history, setHistory] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 5

  useEffect(() => {
    let active = true
    setLoading(true)
    api
      .get(`/api/simulations/me?page=${page}&page_size=${pageSize}`)
      .then((response) => {
        if (!active) return
        setHistory(response.data.items)
        setTotal(response.data.total)
        setSelected((current) => current ?? response.data.items[0] ?? null)
      })
      .catch((requestError) => {
        if (!active) return
        setError(requestError.response?.data?.detail || 'No fue posible cargar el historial.')
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [page])

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">Cliente</p>
        <h1 className="mt-3 text-4xl font-semibold">Historial de simulaciones</h1>
      </section>
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      <SimulationHistoryList
        data={history}
        loading={loading}
        page={page}
        total={total}
        pageSize={pageSize}
        onPageChange={setPage}
        onSelect={setSelected}
        onExport={async (item) => {
          const { exportSimulationToPdf } = await import('../lib/exporters')
          exportSimulationToPdf(item)
        }}
      />
      {selected ? (
        <PanelCard title={`Detalle de simulacion #${selected.id}`} subtitle="Al seleccionar una tarjeta, el frontend recarga el detalle completo para auditoria cientifica.">
          <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-[1.5rem] bg-slate-950 p-4 text-xs text-slate-100">
            {JSON.stringify(selected, null, 2)}
          </pre>
        </PanelCard>
      ) : null}
    </div>
  )
}
