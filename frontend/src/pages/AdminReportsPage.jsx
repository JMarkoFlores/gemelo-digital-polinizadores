import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  AreaChart,
  Area,
} from 'recharts'
import api from '../lib/api'
import MetricCard from '../components/MetricCard'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'
import EmptyState from '../components/EmptyState'

export default function AdminReportsPage() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('operational') // 'operational' | 'management'
  const [filters, setFilters] = useState({
    fecha_inicio: '',
    fecha_fin: '',
    region: '',
    usuario_id: '',
    periodo: 'dia',
    top_n: 10,
  })

  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [operationalData, setOperationalData] = useState(null)
  const [managementData, setManagementData] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    setError('')
    try {
      const opParams = new URLSearchParams()
      if (filters.fecha_inicio) opParams.append('fecha_inicio', filters.fecha_inicio)
      if (filters.fecha_fin) opParams.append('fecha_fin', filters.fecha_fin)
      if (filters.region) opParams.append('region', filters.region)
      if (filters.usuario_id) opParams.append('usuario_id', filters.usuario_id)
      if (filters.periodo) opParams.append('periodo', filters.periodo)

      const mgParams = new URLSearchParams()
      if (filters.fecha_inicio) mgParams.append('fecha_inicio', filters.fecha_inicio)
      if (filters.fecha_fin) mgParams.append('fecha_fin', filters.fecha_fin)
      if (filters.region) mgParams.append('region', filters.region)
      if (filters.usuario_id) mgParams.append('usuario_id', filters.usuario_id)
      if (filters.top_n) mgParams.append('top_n', String(filters.top_n))

      const [opRes, mgRes] = await Promise.all([
        api.get(`/api/admin/reports/operational?${opParams.toString()}`),
        api.get(`/api/admin/reports/management?${mgParams.toString()}`),
      ])

      setOperationalData(opRes.data)
      setManagementData(mgRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || t('adminReports_errorLoad', 'Error al cargar los reportes agregados.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleApplyFilters = (e) => {
    e?.preventDefault()
    fetchData()
  }

  const handleResetFilters = () => {
    setFilters({
      fecha_inicio: '',
      fecha_fin: '',
      region: '',
      usuario_id: '',
      periodo: 'dia',
      top_n: 10,
    })
    setTimeout(() => fetchData(), 50)
  }

  const handleQuickPeriod = (days) => {
    const end = new Date()
    const start = new Date()
    if (days === 'year') {
      start.setFullYear(start.getFullYear(), 0, 1)
    } else if (days === 'all') {
      setFilters((prev) => ({ ...prev, fecha_inicio: '', fecha_fin: '' }))
      return
    } else {
      start.setDate(start.getDate() - days)
    }

    setFilters((prev) => ({
      ...prev,
      fecha_inicio: start.toISOString().split('T')[0],
      fecha_fin: end.toISOString().split('T')[0],
    }))
  }

  // Export handlers
  const handleExportPdf = async () => {
    setExporting(true)
    try {
      const exporters = await import('../lib/generalReportExporters')
      if (activeTab === 'operational' && operationalData) {
        exporters.exportOperationalReportToPdf(operationalData, filters)
      } else if (activeTab === 'management' && managementData) {
        exporters.exportManagementReportToPdf(managementData, filters)
      }
    } catch (err) {
      console.error('Error al exportar PDF:', err)
      setError('Error al generar el documento PDF.')
    } finally {
      setExporting(false)
    }
  }

  const handleExportWord = async () => {
    setExporting(true)
    try {
      const exporters = await import('../lib/generalReportExporters')
      if (activeTab === 'operational' && operationalData) {
        await exporters.exportOperationalReportToDocx(operationalData, filters)
      } else if (activeTab === 'management' && managementData) {
        await exporters.exportManagementReportToDocx(managementData, filters)
      }
    } catch (err) {
      console.error('Error al exportar Word:', err)
      setError('Error al generar el documento Word.')
    } finally {
      setExporting(false)
    }
  }

  const handleExportExcel = async () => {
    setExporting(true)
    try {
      const exporters = await import('../lib/generalReportExporters')
      if (activeTab === 'operational' && operationalData) {
        exporters.exportOperationalReportToExcel(operationalData, filters)
      } else if (activeTab === 'management' && managementData) {
        exporters.exportManagementReportToExcel(managementData, filters)
      }
    } catch (err) {
      console.error('Error al exportar Excel:', err)
      setError('Error al generar el archivo Excel.')
    } finally {
      setExporting(false)
    }
  }

  const opResumen = operationalData?.resumen || {}
  const mgKpis = managementData?.kpis_agroecologicos || {}

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Page Header */}
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('adminReports_badge', 'Panel de Reportes Generales')}
          </span>
          <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-display">
            {t('adminReports_title', 'Reportes Generales y Analítica')}
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
            {t(
              'adminReports_subtitle',
              'Estadísticas agregadas de uso de plataforma y evaluación de impacto agroecológico multiobjetivo.'
            )}
          </p>
        </div>

        {/* Global Export Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleExportPdf}
            disabled={loading || exporting}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            title="Exportar a PDF"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-rose-500"
            >
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>{exporting ? 'Generando...' : 'PDF'}</span>
          </button>

          <button
            onClick={handleExportWord}
            disabled={loading || exporting}
            className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-blue-500 disabled:opacity-50"
            title="Exportar a Word (.docx)"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>Word</span>
          </button>

          <button
            onClick={handleExportExcel}
            disabled={loading || exporting}
            className="inline-flex items-center gap-1.5 rounded-xl bg-green-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-green-500 disabled:opacity-50"
            title="Exportar a Excel (.xlsx)"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            <span>Excel</span>
          </button>
        </div>
      </section>

      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      {/* Filter Panel */}
      <PanelCard
        title={t('adminReports_filterTitle', 'Filtros Globales de Analítica')}
        subtitle={t('adminReports_filterSub', 'Delimita el periodo temporal, territorio y usuarios para el cómputo.')}
      >
        <form onSubmit={handleApplyFilters} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {/* Start Date */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                {t('adminReports_startDate', 'Fecha Inicio')}
              </label>
              <input
                type="date"
                value={filters.fecha_inicio}
                onChange={(e) => setFilters((prev) => ({ ...prev, fecha_inicio: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm text-slate-900 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                {t('adminReports_endDate', 'Fecha Fin')}
              </label>
              <input
                type="date"
                value={filters.fecha_fin}
                onChange={(e) => setFilters((prev) => ({ ...prev, fecha_fin: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm text-slate-900 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>

            {/* Region */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                {t('adminReports_filterRegion', 'Región / Zona')}
              </label>
              <input
                type="text"
                placeholder="Ej. Valle del Cauca, Andina..."
                value={filters.region}
                onChange={(e) => setFilters((prev) => ({ ...prev, region: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>

            {/* User ID */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                {t('adminReports_filterUser', 'Usuario ID (opcional)')}
              </label>
              <input
                type="number"
                placeholder="Ej. 2"
                value={filters.usuario_id}
                onChange={(e) => setFilters((prev) => ({ ...prev, usuario_id: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>
          </div>

          {/* Quick ranges & Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <span className="font-semibold text-slate-700 dark:text-slate-300">Periodo rápido:</span>
              <button
                type="button"
                onClick={() => handleQuickPeriod(7)}
                className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-600 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                7 días
              </button>
              <button
                type="button"
                onClick={() => handleQuickPeriod(30)}
                className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-600 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                30 días
              </button>
              <button
                type="button"
                onClick={() => handleQuickPeriod('year')}
                className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-600 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                Este año
              </button>
              <button
                type="button"
                onClick={() => handleQuickPeriod('all')}
                className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-600 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                Todo
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleResetFilters}
                className="rounded-xl border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {t('adminReports_resetBtn', 'Limpiar')}
              </button>
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-500"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
                {t('adminReports_applyBtn', 'Aplicar Filtros')}
              </button>
            </div>
          </div>
        </form>
      </PanelCard>

      {/* Tabs Switcher */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('operational')}
          className={`relative pb-3.5 px-4 text-sm font-semibold transition-all ${
            activeTab === 'operational'
              ? 'text-emerald-600 dark:text-emerald-400 border-b-2 border-emerald-500'
              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <span className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 3v18h18" />
              <path d="m19 9-5 5-4-4-3 3" />
            </svg>
            1. Reporte Operativo (Uso de Plataforma)
          </span>
        </button>

        <button
          onClick={() => setActiveTab('management')}
          className={`relative pb-3.5 px-4 text-sm font-semibold transition-all ${
            activeTab === 'management'
              ? 'text-emerald-600 dark:text-emerald-400 border-b-2 border-emerald-500'
              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <span className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a9 9 0 0 1 9 9c0 5-4 9-9 9s-9-4-9-9a9 9 0 0 1 9-9Z" />
              <path d="M12 7v5l3 3" />
            </svg>
            2. Reporte de Gestión (KPIs Agroecológicos)
          </span>
        </button>
      </div>

      {loading ? (
        <div className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/60" />
            ))}
          </div>
          <div className="h-72 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/60" />
        </div>
      ) : activeTab === 'operational' ? (
        /* =========================================================
           TAB 1: REPORTE OPERATIVO (Uso de la plataforma)
           ========================================================= */
        <div className="space-y-6">
          {/* KPI Summary */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Total Simulaciones"
              value={opResumen.total_simulaciones ?? 0}
              hint="Ejecutadas en el rango seleccionado."
              tone="emerald"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
                  <polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />
                </svg>
              }
            />

            <MetricCard
              label="Usuarios Activos"
              value={opResumen.usuarios_activos ?? 0}
              hint="Cuentas con simulaciones registradas."
              tone="blue"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-500">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              }
            />

            <MetricCard
              label="Regiones Cubiertas"
              value={opResumen.regiones_cubiertas ?? 0}
              hint="Zonas agroecológicas alcanzadas."
              tone="emerald"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
                  <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" /><line x1="8" y1="2" x2="8" y2="18" /><line x1="16" y1="6" x2="16" y2="22" />
                </svg>
              }
            />

            <MetricCard
              label="Tiempo Promedio Optimización"
              value={
                opResumen.tiempo_promedio_segundos !== null
                  ? `${opResumen.tiempo_promedio_segundos} s`
                  : `~${opResumen.tiempo_estimado_segundos || 1.25} s`
              }
              hint={
                opResumen.tiempo_promedio_disponible
                  ? 'Calculado sobre métricas de ejecución.'
                  : 'Inferencia estimada por iteración NSGA-II.'
              }
              tone="neutral"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
                  <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 14 14" />
                </svg>
              }
            />
          </div>

          {/* Temporal Trend Chart */}
          <PanelCard
            title="Tendencia de Uso de la Plataforma"
            subtitle="Frecuencia y volumen acumulado de simulaciones a lo largo del tiempo."
          >
            {operationalData?.tendencia_temporal?.length === 0 ? (
              <EmptyState title="Sin datos temporales" description="No hay simulaciones en el rango filtrado." />
            ) : (
              <div className="h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={operationalData?.tendencia_temporal} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="opSimGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="periodo" stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        color: '#f8fafc',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Area
                      type="monotone"
                      dataKey="simulaciones"
                      name="Simulaciones periodo"
                      stroke="#10b981"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#opSimGrad)"
                    />
                    <Line
                      type="monotone"
                      dataKey="acumulado"
                      name="Total Acumulado"
                      stroke="#0284c7"
                      strokeWidth={2}
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </PanelCard>

          {/* User Ranking & Regional Distribution Grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* User Ranking */}
            <PanelCard
              title="Ranking de Usuarios Más Activos"
              subtitle="Usuarios ordenados por volumen de escenarios simulados."
            >
              {operationalData?.ranking_usuarios?.length === 0 ? (
                <EmptyState title="Sin usuarios registrados" description="No hay actividad para mostrar." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
                    <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-400">
                      <tr>
                        <th className="px-3 py-2.5">Usuario</th>
                        <th className="px-3 py-2.5">Rol</th>
                        <th className="px-3 py-2.5 text-center">Simulaciones</th>
                        <th className="px-3 py-2.5 text-right">Última Simulación</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {operationalData?.ranking_usuarios?.map((u, idx) => (
                        <tr key={u.usuario_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                          <td className="px-3 py-2.5 font-medium text-slate-900 dark:text-slate-100 flex items-center gap-2">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/10 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                              {idx + 1}
                            </span>
                            <span className="truncate max-w-[150px]" title={u.email}>
                              {u.email}
                            </span>
                          </td>
                          <td className="px-3 py-2.5">
                            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                              {u.rol}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-center font-bold text-emerald-600 dark:text-emerald-400">
                            {u.total_simulaciones}
                          </td>
                          <td className="px-3 py-2.5 text-right text-slate-400">
                            {u.ultima_simulacion ? new Date(u.ultima_simulacion).toLocaleDateString() : 'N/D'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </PanelCard>

            {/* Regions Distribution */}
            <PanelCard
              title="Regiones Más Simuladas"
              subtitle="Concentración de parcelas por zona agroecológica."
            >
              {operationalData?.distribucion_regiones?.length === 0 ? (
                <EmptyState title="Sin regiones" description="No hay parcelas registradas." />
              ) : (
                <div className="space-y-3.5 pt-1">
                  {operationalData?.distribucion_regiones?.map((r) => (
                    <div key={r.region} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="text-slate-800 dark:text-slate-200">{r.region}</span>
                        <span className="text-slate-500 dark:text-slate-400">
                          {r.total} ({r.porcentaje}%)
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
                          style={{ width: `${Math.min(100, Math.max(5, r.porcentaje))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </PanelCard>
          </div>
        </div>
      ) : (
        /* =========================================================
           TAB 2: REPORTE DE GESTIÓN (KPIs agroecológicos agregados)
           ========================================================= */
        <div className="space-y-6">
          {/* Management KPI Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Rendimiento Agrícola Promedio"
              value={`${mgKpis.rendimiento_promedio_optimo?.toFixed(1) || 0} pts`}
              hint={`Base: ${mgKpis.rendimiento_promedio_base?.toFixed(1) || 0} (Δ +${mgKpis.delta_rendimiento_promedio?.toFixed(1) || 0} pts, +${mgKpis.delta_rendimiento_pct?.toFixed(1) || 0}%)`}
              tone="emerald"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
                  <path d="M12 2v20" /><path d="m17 5-5-3-5 3" /><path d="m17 19-5 3-5-3" />
                </svg>
              }
            />

            <MetricCard
              label="Abundancia de Polinizadores"
              value={`${mgKpis.abundancia_polinizadores_optima?.toFixed(1) || 0} pts`}
              hint={`Base: ${mgKpis.abundancia_polinizadores_base?.toFixed(1) || 0} (Δ +${mgKpis.delta_abundancia_promedio?.toFixed(1) || 0} pts, +${mgKpis.delta_abundancia_pct?.toFixed(1) || 0}%)`}
              tone="emerald"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
                  <circle cx="12" cy="12" r="4" /><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8" />
                </svg>
              }
            />

            <MetricCard
              label="Diversidad de Polinizadores"
              value={`${mgKpis.diversidad_polinizadores_optima?.toFixed(2) || 0} pts`}
              hint={`Línea base: ${mgKpis.diversidad_polinizadores_base?.toFixed(2) || 0} (Δ +${mgKpis.delta_diversidad_promedio?.toFixed(2) || 0})`}
              tone="blue"
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-500">
                  <path d="M12 2a9 9 0 0 1 9 9c0 5-4 9-9 9s-9-4-9-9a9 9 0 0 1 9-9Z" />
                </svg>
              }
            />

            <MetricCard
              label="Tasa Cumplimiento Hipótesis"
              value={`${mgKpis.tasa_cumplimiento_hipotesis?.toFixed(1) || 0}%`}
              hint={`+20% polinizadores con Δyield ≥ 0 (${mgKpis.simulaciones_cumplen_hipotesis || 0} de ${mgKpis.total_simulaciones || 0})`}
              tone={mgKpis.tasa_cumplimiento_hipotesis >= 70 ? 'emerald' : 'neutral'}
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              }
            />
          </div>

          {/* Temporal Evolution Chart */}
          <PanelCard
            title="Evolución Agroecológica en el Tiempo"
            subtitle="Comparativa de Rendimiento Agrícola y Abundancia de Polinizadores (Línea Base vs Óptimo)."
          >
            {managementData?.evolucion_temporal?.length === 0 ? (
              <EmptyState title="Sin datos de evolución" description="No hay registros en el periodo seleccionado." />
            ) : (
              <div className="h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={managementData?.evolucion_temporal} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="fecha" stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        color: '#f8fafc',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Line
                      type="monotone"
                      dataKey="rendimiento_optimo"
                      name="Rendimiento Óptimo"
                      stroke="#10b981"
                      strokeWidth={2.5}
                    />
                    <Line
                      type="monotone"
                      dataKey="rendimiento_base"
                      name="Rendimiento Base"
                      stroke="#94a3b8"
                      strokeDasharray="4 4"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="abundancia_optima"
                      name="Abundancia Polinizadores (Ópt.)"
                      stroke="#f59e0b"
                      strokeWidth={2.5}
                    />
                    <Line
                      type="monotone"
                      dataKey="abundancia_base"
                      name="Abundancia Polinizadores (Base)"
                      stroke="#fcd34d"
                      strokeDasharray="4 4"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </PanelCard>

          {/* Regional Comparison Grouped Bar Chart */}
          <PanelCard
            title="Comparativa Multiobjetivo por Región Agroecológica"
            subtitle="Rendimiento agrícola, abundancia de polinizadores y tasa de comprobación de hipótesis por territorio."
          >
            {managementData?.comparacion_regiones?.length === 0 ? (
              <EmptyState title="Sin datos regionales" description="No hay simulaciones en el rango filtrado." />
            ) : (
              <div className="h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={managementData?.comparacion_regiones} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="region" stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        borderRadius: '0.75rem',
                        color: '#f8fafc',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Bar dataKey="rendimiento_promedio_optimo" name="Rendimiento Óptimo" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="abundancia_promedio_optimo" name="Abundancia Polinizadores" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="tasa_cumplimiento_hipotesis" name="% Hipótesis Comprobada" fill="#0284c7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </PanelCard>

          {/* Top Pareto Configurations Table */}
          <PanelCard
            title="Top Mejores Configuraciones de Paisaje (Frente de Pareto)"
            subtitle="Soluciones no dominadas óptimas que maximizan conservación biológica y productividad agrícola."
          >
            {managementData?.top_configuraciones_pareto?.length === 0 ? (
              <EmptyState title="Sin configuraciones" description="No se encontraron soluciones de Pareto." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
                  <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-2.5">Rank</th>
                      <th className="px-3 py-2.5">Región</th>
                      <th className="px-3 py-2.5 text-center">Rendimiento</th>
                      <th className="px-3 py-2.5 text-center">Abundancia</th>
                      <th className="px-3 py-2.5 text-center">Diversidad</th>
                      <th className="px-3 py-2.5 text-center">% Cultivo</th>
                      <th className="px-3 py-2.5 text-center">% Área Nat.</th>
                      <th className="px-3 py-2.5 text-center">% Franjas</th>
                      <th className="px-3 py-2.5 text-center">Pesticidas</th>
                      <th className="px-3 py-2.5 text-right">Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {managementData?.top_configuraciones_pareto?.map((p) => (
                      <tr key={`${p.simulacion_id}-${p.rank}`} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <td className="px-3 py-2.5 font-bold text-slate-900 dark:text-slate-100">
                          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/10 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                            #{p.rank}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 font-semibold text-slate-800 dark:text-slate-200">{p.region}</td>
                        <td className="px-3 py-2.5 text-center font-bold text-emerald-600 dark:text-emerald-400">
                          {p.crop_yield_index?.toFixed(1)}
                        </td>
                        <td className="px-3 py-2.5 text-center font-bold text-amber-500">
                          {p.pollinator_abundance_index?.toFixed(1)}
                        </td>
                        <td className="px-3 py-2.5 text-center text-sky-600 dark:text-sky-400">
                          {p.pollinator_diversity_index?.toFixed(2)}
                        </td>
                        <td className="px-3 py-2.5 text-center">{p.crop_area_pct}%</td>
                        <td className="px-3 py-2.5 text-center text-emerald-600 dark:text-emerald-400 font-medium">
                          {p.natural_area_pct}%
                        </td>
                        <td className="px-3 py-2.5 text-center text-amber-600 dark:text-amber-400 font-medium">
                          {p.floral_strips_pct}%
                        </td>
                        <td className="px-3 py-2.5 text-center text-slate-500">{p.pesticide_level}</td>
                        <td className="px-3 py-2.5 text-right font-extrabold text-slate-900 dark:text-slate-100">
                          {p.score?.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </PanelCard>
        </div>
      )}
    </div>
  )
}
