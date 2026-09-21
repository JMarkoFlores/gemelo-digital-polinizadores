import * as XLSX from 'xlsx'
import jsPDF from 'jspdf'
import {
  Document,
  Packer,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  HeadingLevel,
  AlignmentType,
  ImageRun,
} from 'docx'
import { saveAs } from 'file-saver'

function getTimestamp() {
  const d = new Date()
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}_${String(d.getHours()).padStart(2, '0')}${String(d.getMinutes()).padStart(2, '0')}`
}

function formatVal(v, decimals = 2) {
  if (v === undefined || v === null) return 'N/D'
  if (typeof v === 'number') return v.toFixed(decimals)
  return String(v)
}

function formatFilterDate(d) {
  if (!d) return 'Todas'
  try {
    return new Date(d).toLocaleDateString()
  } catch {
    return String(d)
  }
}

function base64ToUint8Array(base64Str) {
  if (!base64Str) return null
  try {
    const clean = base64Str.replace(/^data:image\/\w+;base64,/, '')
    const binary = atob(clean)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    return bytes
  } catch (err) {
    console.error('Error al decodificar base64 a Uint8Array:', err)
    return null
  }
}

// ==========================================
// 1. REPORTE OPERATIVO - EXPORTADORES
// ==========================================

export function exportOperationalReportToPdf(reportData, filters = {}, charts = {}) {
  const doc = new jsPDF()
  const margin = 14
  let y = 18

  // Header Banner
  doc.setFillColor(16, 185, 129) // Emerald-500
  doc.rect(margin, y, 182, 14, 'F')
  doc.setFontSize(14)
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.text('GEMELOS DIGITALES | REPORTE OPERATIVO DE PLATAFORMA', margin + 6, y + 9.5)
  y += 20

  // Subtitle
  doc.setFontSize(9)
  doc.setTextColor(100, 116, 139)
  doc.setFont('helvetica', 'normal')
  const nowStr = new Date().toLocaleString()
  doc.text(`Fecha de emisión: ${nowStr}  |  Ámbito: Trazabilidad y supervisión del uso global`, margin, y)
  y += 7

  // Filter Box
  doc.setFillColor(248, 250, 252)
  doc.setDrawColor(226, 232, 240)
  doc.roundedRect(margin, y, 182, 16, 2, 2, 'FD')
  doc.setFontSize(8.5)
  doc.setTextColor(51, 65, 85)
  const fStart = formatFilterDate(filters.fecha_inicio)
  const fEnd = formatFilterDate(filters.fecha_fin)
  const fReg = filters.region || 'Todas las regiones'
  const fUsr = filters.usuario_id ? `#${filters.usuario_id}` : 'Todos'
  doc.text(`Filtros: Periodo [${fStart} - ${fEnd}]  |  Región: ${fReg}  |  Usuario: ${fUsr}`, margin + 4, y + 10)
  y += 22

  // Summary KPI Cards Box
  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.setFont('helvetica', 'bold')
  doc.text('1. Indicadores Operativos Clave', margin, y)
  y += 5

  const resumen = reportData.resumen || {}
  const cardW = 43
  const cardH = 18
  const cards = [
    { label: 'Total Simulaciones', val: String(resumen.total_simulaciones ?? 0) },
    { label: 'Usuarios Activos', val: String(resumen.usuarios_activos ?? 0) },
    { label: 'Regiones Cubiertas', val: String(resumen.regiones_cubiertas ?? 0) },
    {
      label: 'Tiempo Promedio',
      val: resumen.tiempo_promedio_segundos !== null ? `${resumen.tiempo_promedio_segundos}s` : `~${resumen.tiempo_estimado_segundos || 1.25}s (est.)`,
    },
  ]

  cards.forEach((c, idx) => {
    const cx = margin + idx * (cardW + 3.3)
    doc.setFillColor(241, 245, 249)
    doc.roundedRect(cx, y, cardW, cardH, 2, 2, 'F')
    doc.setFontSize(7.5)
    doc.setTextColor(100, 116, 139)
    doc.setFont('helvetica', 'normal')
    doc.text(c.label, cx + 3, y + 6)
    doc.setFontSize(11)
    doc.setTextColor(16, 185, 129)
    doc.setFont('helvetica', 'bold')
    doc.text(c.val, cx + 3, y + 14)
  })
  y += 24

  // Chart 1: Embedded Trend Chart Image
  if (charts.trend_chart_base64) {
    doc.setFontSize(11)
    doc.setTextColor(15, 23, 42)
    doc.setFont('helvetica', 'bold')
    doc.text('2. Gráfica de Tendencia de Uso de la Plataforma', margin, y)
    y += 4

    try {
      const imgData = 'data:image/png;base64,' + charts.trend_chart_base64
      doc.addImage(imgData, 'PNG', margin, y, 182, 68)
      y += 73
    } catch (e) {
      console.warn('Error al embeber imagen de gráfica en PDF:', e)
    }
  }

  // Section 3: Ranking de Usuarios
  if (y > 215) {
    doc.addPage()
    y = 20
  }

  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.setFont('helvetica', 'bold')
  doc.text('3. Ranking de Usuarios Más Activos', margin, y)
  y += 6

  doc.setFillColor(226, 232, 240)
  doc.rect(margin, y, 182, 6, 'F')
  doc.setFontSize(8)
  doc.setTextColor(30, 41, 59)
  doc.text('ID', margin + 3, y + 4.2)
  doc.text('Correo Electrónico', margin + 20, y + 4.2)
  doc.text('Rol', margin + 95, y + 4.2)
  doc.text('N° Simulaciones', margin + 120, y + 4.2)
  doc.text('Última Actividad', margin + 152, y + 4.2)
  y += 6.5

  const usuarios = (reportData.ranking_usuarios || []).slice(0, 10)
  doc.setFont('helvetica', 'normal')
  usuarios.forEach((u, i) => {
    if (i % 2 === 1) {
      doc.setFillColor(248, 250, 252)
      doc.rect(margin, y, 182, 5.5, 'F')
    }
    doc.text(String(u.usuario_id), margin + 3, y + 4)
    doc.text(String(u.email), margin + 20, y + 4)
    doc.text(String(u.rol), margin + 95, y + 4)
    doc.text(String(u.total_simulaciones), margin + 130, y + 4)
    const dtStr = u.ultima_simulacion ? new Date(u.ultima_simulacion).toLocaleDateString() : 'N/D'
    doc.text(dtStr, margin + 152, y + 4)
    y += 5.5
  })
  y += 8

  // Section 4: Regiones Más Simuladas
  if (y > 215) {
    doc.addPage()
    y = 20
  }

  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.setFont('helvetica', 'bold')
  doc.text('4. Distribución por Región Agroecológica', margin, y)
  y += 6

  doc.setFillColor(226, 232, 240)
  doc.rect(margin, y, 182, 6, 'F')
  doc.setFontSize(8)
  doc.setTextColor(30, 41, 59)
  doc.text('Región / Zona Agroecológica', margin + 4, y + 4.2)
  doc.text('Total Simulaciones', margin + 105, y + 4.2)
  doc.text('% de Participación', margin + 150, y + 4.2)
  y += 6.5

  const regiones = reportData.distribucion_regiones || []
  doc.setFont('helvetica', 'normal')
  regiones.forEach((r, i) => {
    if (i % 2 === 1) {
      doc.setFillColor(248, 250, 252)
      doc.rect(margin, y, 182, 5.5, 'F')
    }
    doc.text(String(r.region), margin + 4, y + 4)
    doc.text(String(r.total), margin + 115, y + 4)
    doc.text(`${formatVal(r.porcentaje, 1)}%`, margin + 158, y + 4)
    y += 5.5
  })

  // Footer
  doc.setFontSize(8)
  doc.setTextColor(148, 163, 184)
  doc.text('Gemelo Digital de Polinizadores © 2026 - Módulo de Reportes de Gestión y Operación', margin, 285)

  doc.save(`Reporte_Operativo_GemeloDigital_${getTimestamp()}.pdf`)
}

export async function exportOperationalReportToDocx(reportData, filters = {}, charts = {}) {
  const resumen = reportData.resumen || {}
  const cardData = [
    { metrica: 'Total de Simulaciones', valor: String(resumen.total_simulaciones ?? 0) },
    { metrica: 'Usuarios Activos', valor: String(resumen.usuarios_activos ?? 0) },
    { metrica: 'Regiones Cubiertas', valor: String(resumen.regiones_cubiertas ?? 0) },
    {
      metrica: 'Tiempo Promedio de Optimización',
      valor: resumen.tiempo_promedio_segundos !== null ? `${resumen.tiempo_promedio_segundos} s` : `~${resumen.tiempo_estimado_segundos || 1.25} s (estimado)`,
    },
  ]

  const createTableRow = (c1, c2, c3, isHeader = false) => {
    return new TableRow({
      children: [
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: c1, bold: isHeader })] })] }),
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: c2, bold: isHeader })] })] }),
        ...(c3 !== undefined ? [new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: c3, bold: isHeader })] })] })] : []),
      ],
    })
  }

  const kpiRows = [
    createTableRow('Indicador Operativo', 'Valor Registrado', undefined, true),
    ...cardData.map((c) => createTableRow(c.metrica, c.valor)),
  ]

  const tendenciaRows = [
    createTableRow('Periodo', 'Simulaciones', 'Acumulado', true),
    ...(reportData.tendencia_temporal || []).map((pt) => createTableRow(String(pt.periodo), String(pt.simulaciones), String(pt.acumulado))),
  ]

  const regionRows = [
    createTableRow('Región / Zona', 'Total Simulaciones', 'Porcentaje', true),
    ...(reportData.distribucion_regiones || []).map((r) => createTableRow(String(r.region), String(r.total), `${formatVal(r.porcentaje, 1)}%`)),
  ]

  const userRows = [
    new TableRow({
      children: [
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: 'ID', bold: true })] })] }),
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: 'Correo', bold: true })] })] }),
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: 'Rol', bold: true })] })] }),
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: 'Simulaciones', bold: true })] })] }),
      ],
    }),
    ...(reportData.ranking_usuarios || []).map((u) => new TableRow({
      children: [
        new TableCell({ children: [new Paragraph(String(u.usuario_id))] }),
        new TableCell({ children: [new Paragraph(String(u.email))] }),
        new TableCell({ children: [new Paragraph(String(u.rol))] }),
        new TableCell({ children: [new Paragraph(String(u.total_simulaciones))] }),
      ],
    })),
  ]

  // Optional Chart ImageRun
  const chartRuns = []
  if (charts.trend_chart_base64) {
    const u8 = base64ToUint8Array(charts.trend_chart_base64)
    if (u8) {
      chartRuns.push(
        new Paragraph({ text: '2. Gráfica de Tendencia de Uso de la Plataforma', heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new ImageRun({
              data: u8,
              transformation: { width: 560, height: 235 },
            }),
          ],
        }),
        new Paragraph({ text: '', spacing: { after: 200 } })
      )
    }
  }

  const doc = new Document({
    sections: [{
      properties: {},
      children: [
        new Paragraph({ text: 'Plataforma Gemelos Digitales de Polinizadores', heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER }),
        new Paragraph({ text: 'Reporte Operativo y de Uso Global', heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER }),
        new Paragraph({ text: `Fecha de emisión: ${new Date().toLocaleString()}`, alignment: AlignmentType.CENTER, spacing: { after: 200 } }),
        new Paragraph({ text: '1. Resumen de Indicadores Clave', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: kpiRows }),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        ...chartRuns,

        new Paragraph({ text: '3. Tendencia de Simulaciones por Periodo', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: tendenciaRows }),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        new Paragraph({ text: '4. Ranking de Usuarios Más Activos', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: userRows }),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        new Paragraph({ text: '5. Distribución por Región', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: regionRows }),
      ],
    }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `Reporte_Operativo_GemeloDigital_${getTimestamp()}.docx`)
}

export function exportOperationalReportToExcel(reportData, filters = {}) {
  const wb = XLSX.utils.book_new()
  const resumen = reportData.resumen || {}

  const wsResumen = XLSX.utils.json_to_sheet([
    { Parametro: 'Fecha Emisión', Valor: new Date().toLocaleString() },
    { Parametro: 'Filtro Fecha Inicio', Valor: formatFilterDate(filters.fecha_inicio) },
    { Parametro: 'Filtro Fecha Fin', Valor: formatFilterDate(filters.fecha_fin) },
    { Parametro: 'Filtro Región', Valor: filters.region || 'Todas' },
    { Parametro: 'Filtro Usuario', Valor: filters.usuario_id || 'Todos' },
    { Parametro: 'Total de Simulaciones', Valor: resumen.total_simulaciones ?? 0 },
    { Parametro: 'Usuarios Activos', Valor: resumen.usuarios_activos ?? 0 },
    { Parametro: 'Regiones Cubiertas', Valor: resumen.regiones_cubiertas ?? 0 },
    {
      Parametro: 'Tiempo Promedio (s)',
      Valor: resumen.tiempo_promedio_segundos !== null ? resumen.tiempo_promedio_segundos : `~${resumen.tiempo_estimado_segundos || 1.25} (estimado)`,
    },
  ])
  wsResumen['!cols'] = [{ wch: 30 }, { wch: 35 }]
  XLSX.utils.book_append_sheet(wb, wsResumen, 'Resumen_Operativo')

  const wsTendencia = XLSX.utils.json_to_sheet((reportData.tendencia_temporal || []).map((pt) => ({
    Periodo: pt.periodo,
    Simulaciones: pt.simulaciones,
    Acumulado: pt.acumulado,
  })))
  wsTendencia['!cols'] = [{ wch: 20 }, { wch: 18 }, { wch: 18 }]
  XLSX.utils.book_append_sheet(wb, wsTendencia, 'Tendencia_Temporal')

  const wsUsers = XLSX.utils.json_to_sheet((reportData.ranking_usuarios || []).map((u) => ({
    Usuario_ID: u.usuario_id,
    Email: u.email,
    Rol: u.rol,
    Total_Simulaciones: u.total_simulaciones,
    Ultima_Simulacion: u.ultima_simulacion || 'N/D',
  })))
  wsUsers['!cols'] = [{ wch: 14 }, { wch: 32 }, { wch: 14 }, { wch: 20 }, { wch: 24 }]
  XLSX.utils.book_append_sheet(wb, wsUsers, 'Ranking_Usuarios')

  const wsReg = XLSX.utils.json_to_sheet((reportData.distribucion_regiones || []).map((r) => ({
    Region: r.region,
    Total_Simulaciones: r.total,
    Porcentaje_Total: `${formatVal(r.porcentaje, 1)}%`,
  })))
  wsReg['!cols'] = [{ wch: 30 }, { wch: 20 }, { wch: 18 }]
  XLSX.utils.book_append_sheet(wb, wsReg, 'Distribucion_Regiones')

  XLSX.writeFile(wb, `Reporte_Operativo_GemeloDigital_${getTimestamp()}.xlsx`)
}

// ==========================================
// 2. REPORTE DE GESTIÓN - EXPORTADORES
// ==========================================

export function exportManagementReportToPdf(reportData, filters = {}, charts = {}) {
  const doc = new jsPDF()
  const margin = 14
  let y = 18

  // Header Banner
  doc.setFillColor(5, 150, 105) // Emerald-600
  doc.rect(margin, y, 182, 14, 'F')
  doc.setFontSize(13.5)
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.text('GEMELOS DIGITALES | REPORTE DE GESTIÓN AGROECOLÓGICA', margin + 6, y + 9.5)
  y += 20

  // Subtitle
  doc.setFontSize(9)
  doc.setTextColor(100, 116, 139)
  doc.setFont('helvetica', 'normal')
  const nowStr = new Date().toLocaleString()
  doc.text(`Fecha de emisión: ${nowStr}  |  Evaluación agregada de impacto agronómico y biológico`, margin, y)
  y += 7

  // Filter Box
  doc.setFillColor(248, 250, 252)
  doc.setDrawColor(226, 232, 240)
  doc.roundedRect(margin, y, 182, 16, 2, 2, 'FD')
  doc.setFontSize(8.5)
  doc.setTextColor(51, 65, 85)
  const fStart = formatFilterDate(filters.fecha_inicio)
  const fEnd = formatFilterDate(filters.fecha_fin)
  const fReg = filters.region || 'Todas las regiones'
  doc.text(`Filtros: Periodo [${fStart} - ${fEnd}]  |  Región: ${fReg}  |  Criterio Hipótesis: ΔAbundancia ≥ 20% y ΔRendimiento ≥ 0`, margin + 4, y + 10)
  y += 22

  // Agroecological KPIs
  const kpis = reportData.kpis_agroecologicos || {}
  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.setFont('helvetica', 'bold')
  doc.text('1. Indicadores Agroecológicos y Cumplimiento de Hipótesis', margin, y)
  y += 5

  const cardW = 43
  const cardH = 20
  const mgCards = [
    {
      label: 'Rendimiento Agrícola',
      main: `${formatVal(kpis.rendimiento_promedio_optimo, 1)} pts`,
      sub: `Δ +${formatVal(kpis.delta_rendimiento_promedio, 1)} (${formatVal(kpis.delta_rendimiento_pct, 1)}%)`,
    },
    {
      label: 'Abundancia Poliniz.',
      main: `${formatVal(kpis.abundancia_polinizadores_optima, 1)} pts`,
      sub: `Δ +${formatVal(kpis.delta_abundancia_promedio, 1)} (+${formatVal(kpis.delta_abundancia_pct, 1)}%)`,
    },
    {
      label: 'Diversidad Poliniz.',
      main: `${formatVal(kpis.diversidad_polinizadores_optima, 2)} pts`,
      sub: `Δ +${formatVal(kpis.delta_diversidad_promedio, 2)}`,
    },
    {
      label: 'Cumplimiento Hipótesis',
      main: `${formatVal(kpis.tasa_cumplimiento_hipotesis, 1)}%`,
      sub: `${kpis.simulaciones_cumplen_hipotesis || 0} de ${kpis.total_simulaciones || 0} parcelas`,
    },
  ]

  mgCards.forEach((c, idx) => {
    const cx = margin + idx * (cardW + 3.3)
    doc.setFillColor(241, 245, 249)
    doc.roundedRect(cx, y, cardW, cardH, 2, 2, 'F')
    doc.setFontSize(7.5)
    doc.setTextColor(100, 116, 139)
    doc.setFont('helvetica', 'normal')
    doc.text(c.label, cx + 3, y + 5.5)
    doc.setFontSize(10.5)
    doc.setTextColor(5, 150, 105)
    doc.setFont('helvetica', 'bold')
    doc.text(c.main, cx + 3, y + 12.5)
    doc.setFontSize(7)
    doc.setTextColor(71, 85, 105)
    doc.setFont('helvetica', 'normal')
    doc.text(c.sub, cx + 3, y + 17.5)
  })
  y += 26

  // Chart 1: Evolution Chart Image
  if (charts.evolution_chart_base64) {
    doc.setFontSize(11)
    doc.setTextColor(15, 23, 42)
    doc.setFont('helvetica', 'bold')
    doc.text('2. Evolución Agroecológica en el Tiempo', margin, y)
    y += 4

    try {
      const imgData = 'data:image/png;base64,' + charts.evolution_chart_base64
      doc.addImage(imgData, 'PNG', margin, y, 182, 68)
      y += 73
    } catch (e) {
      console.warn('Error al embeber imagen de evolución en PDF:', e)
    }
  }

  // Chart 2: Regional Multiobjective Chart Image
  if (charts.regional_chart_base64) {
    if (y > 210) {
      doc.addPage()
      y = 20
    }
    doc.setFontSize(11)
    doc.setTextColor(15, 23, 42)
    doc.setFont('helvetica', 'bold')
    doc.text('3. Comparativa Multiobjetivo por Región', margin, y)
    y += 4

    try {
      const imgData = 'data:image/png;base64,' + charts.regional_chart_base64
      doc.addImage(imgData, 'PNG', margin, y, 182, 68)
      y += 73
    } catch (e) {
      console.warn('Error al embeber imagen regional en PDF:', e)
    }
  }

  // Section 4: Regional Comparison Table
  if (y > 215) {
    doc.addPage()
    y = 20
  }
  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.setFont('helvetica', 'bold')
  doc.text('4. Métricas Comparativas por Región Agroecológica', margin, y)
  y += 6

  doc.setFillColor(226, 232, 240)
  doc.rect(margin, y, 182, 6, 'F')
  doc.setFontSize(7.5)
  doc.setTextColor(30, 41, 59)
  doc.text('Región', margin + 3, y + 4.2)
  doc.text('Simulaciones', margin + 50, y + 4.2)
  doc.text('Rendimiento Prom.', margin + 78, y + 4.2)
  doc.text('Abundancia Prom.', margin + 112, y + 4.2)
  doc.text('Diversidad Prom.', margin + 145, y + 4.2)
  doc.text('% Hipótesis', margin + 168, y + 4.2)
  y += 6.5

  const compReg = reportData.comparacion_regiones || []
  doc.setFont('helvetica', 'normal')
  compReg.forEach((cr, i) => {
    if (i % 2 === 1) {
      doc.setFillColor(248, 250, 252)
      doc.rect(margin, y, 182, 5.5, 'F')
    }
    doc.text(String(cr.region), margin + 3, y + 4)
    doc.text(String(cr.total_simulaciones), margin + 55, y + 4)
    doc.text(formatVal(cr.rendimiento_promedio_optimo, 1), margin + 85, y + 4)
    doc.text(formatVal(cr.abundancia_promedio_optimo, 1), margin + 118, y + 4)
    doc.text(formatVal(cr.diversidad_promedio_optimo, 2), margin + 148, y + 4)
    doc.text(`${formatVal(cr.tasa_cumplimiento_hipotesis, 1)}%`, margin + 169, y + 4)
    y += 5.5
  })
  y += 8

  // Section 5: Top Pareto Front Configurations
  if (y > 200) {
    doc.addPage()
    y = 20
  }
  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.setFont('helvetica', 'bold')
  doc.text('5. Top Mejores Configuraciones de Paisaje (Frente de Pareto)', margin, y)
  y += 6

  doc.setFillColor(226, 232, 240)
  doc.rect(margin, y, 182, 6, 'F')
  doc.setFontSize(7)
  doc.setTextColor(30, 41, 59)
  doc.text('#', margin + 2, y + 4.2)
  doc.text('Región', margin + 8, y + 4.2)
  doc.text('Rendimiento', margin + 50, y + 4.2)
  doc.text('Polinizadores', margin + 74, y + 4.2)
  doc.text('Diversidad', margin + 98, y + 4.2)
  doc.text('% Cultivo', margin + 118, y + 4.2)
  doc.text('% Nat.', margin + 135, y + 4.2)
  doc.text('% Franjas', margin + 150, y + 4.2)
  doc.text('Score', margin + 168, y + 4.2)
  y += 6.5

  const topPareto = (reportData.top_configuraciones_pareto || []).slice(0, 10)
  doc.setFont('helvetica', 'normal')
  topPareto.forEach((p, i) => {
    if (i % 2 === 1) {
      doc.setFillColor(248, 250, 252)
      doc.rect(margin, y, 182, 5.5, 'F')
    }
    doc.text(String(p.rank), margin + 2, y + 4)
    doc.text(String(p.region), margin + 8, y + 4)
    doc.text(formatVal(p.crop_yield_index, 1), margin + 53, y + 4)
    doc.text(formatVal(p.pollinator_abundance_index, 1), margin + 78, y + 4)
    doc.text(formatVal(p.pollinator_diversity_index, 2), margin + 100, y + 4)
    doc.text(`${formatVal(p.crop_area_pct, 1)}%`, margin + 120, y + 4)
    doc.text(`${formatVal(p.natural_area_pct, 1)}%`, margin + 136, y + 4)
    doc.text(`${formatVal(p.floral_strips_pct, 1)}%`, margin + 152, y + 4)
    doc.text(formatVal(p.score, 1), margin + 168, y + 4)
    y += 5.5
  })

  // Footer
  doc.setFontSize(8)
  doc.setTextColor(148, 163, 184)
  doc.text('Gemelo Digital de Polinizadores © 2026 - Módulo de Reportes de Gestión y Operación', margin, 285)

  doc.save(`Reporte_Gestion_Agroecologica_${getTimestamp()}.pdf`)
}

export async function exportManagementReportToDocx(reportData, filters = {}, charts = {}) {
  const kpis = reportData.kpis_agroecologicos || {}

  const createTableRow = (cols, isHeader = false) => {
    return new TableRow({
      children: cols.map(
        (txt) =>
          new TableCell({
            children: [new Paragraph({ children: [new TextRun({ text: String(txt), bold: isHeader })] })],
          })
      ),
    })
  }

  const kpiRows = [
    createTableRow(['Métrica Agroecológica', 'Línea Base', 'Óptimo Obtenido', 'Delta Variación'], true),
    createTableRow([
      'Rendimiento Agrícola (crop_yield_index)',
      formatVal(kpis.rendimiento_promedio_base, 2),
      formatVal(kpis.rendimiento_promedio_optimo, 2),
      `+${formatVal(kpis.delta_rendimiento_promedio, 2)} (+${formatVal(kpis.delta_rendimiento_pct, 1)}%)`,
    ]),
    createTableRow([
      'Abundancia Polinizadores (pollinator_abundance_index)',
      formatVal(kpis.abundancia_polinizadores_base, 2),
      formatVal(kpis.abundancia_polinizadores_optima, 2),
      `+${formatVal(kpis.delta_abundancia_promedio, 2)} (+${formatVal(kpis.delta_abundancia_pct, 1)}%)`,
    ]),
    createTableRow([
      'Diversidad Polinizadores (pollinator_diversity_index)',
      formatVal(kpis.diversidad_polinizadores_base, 2),
      formatVal(kpis.diversidad_polinizadores_optima, 2),
      `+${formatVal(kpis.delta_diversidad_promedio, 2)}`,
    ]),
    createTableRow([
      'Tasa de Cumplimiento de Hipótesis Ecológica',
      'Objetivo: ≥20% pol. con Δyield ≥ 0',
      `${formatVal(kpis.tasa_cumplimiento_hipotesis, 1)}%`,
      `${kpis.simulaciones_cumplen_hipotesis || 0} de ${kpis.total_simulaciones || 0} parcelas`,
    ]),
  ]

  const regionRows = [
    createTableRow(['Región', 'Simulaciones', 'Rendimiento Óptimo', 'Abundancia Óptima', 'Diversidad', '% Hipótesis'], true),
    ...(reportData.comparacion_regiones || []).map((cr) =>
      createTableRow([
        cr.region,
        cr.total_simulaciones,
        formatVal(cr.rendimiento_promedio_optimo, 2),
        formatVal(cr.abundancia_promedio_optimo, 2),
        formatVal(cr.diversidad_promedio_optimo, 2),
        `${formatVal(cr.tasa_cumplimiento_hipotesis, 1)}%`,
      ])
    ),
  ]

  const paretoRows = [
    createTableRow(['Rank', 'Región', 'Rendimiento', 'Polinizadores', 'Diversidad', '% Cultivo', '% Área Nat.', '% Franjas', 'Score'], true),
    ...(reportData.top_configuraciones_pareto || []).map((p) =>
      createTableRow([
        p.rank,
        p.region,
        formatVal(p.crop_yield_index, 2),
        formatVal(p.pollinator_abundance_index, 2),
        formatVal(p.pollinator_diversity_index, 2),
        `${formatVal(p.crop_area_pct, 1)}%`,
        `${formatVal(p.natural_area_pct, 1)}%`,
        `${formatVal(p.floral_strips_pct, 1)}%`,
        formatVal(p.score, 2),
      ])
    ),
  ]

  // Optional Chart ImageRuns
  const chartRuns = []
  if (charts.evolution_chart_base64) {
    const u8 = base64ToUint8Array(charts.evolution_chart_base64)
    if (u8) {
      chartRuns.push(
        new Paragraph({ text: '2. Gráfica de Evolución Agroecológica en el Tiempo', heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new ImageRun({
              data: u8,
              transformation: { width: 560, height: 240 },
            }),
          ],
        }),
        new Paragraph({ text: '', spacing: { after: 200 } })
      )
    }
  }

  if (charts.regional_chart_base64) {
    const u8 = base64ToUint8Array(charts.regional_chart_base64)
    if (u8) {
      chartRuns.push(
        new Paragraph({ text: '3. Gráfica de Comparativa Multiobjetivo por Región', heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new ImageRun({
              data: u8,
              transformation: { width: 560, height: 240 },
            }),
          ],
        }),
        new Paragraph({ text: '', spacing: { after: 200 } })
      )
    }
  }

  const doc = new Document({
    sections: [{
      properties: {},
      children: [
        new Paragraph({ text: 'Plataforma Gemelos Digitales de Polinizadores', heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER }),
        new Paragraph({ text: 'Reporte de Gestión Agroecológica Agregada', heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER }),
        new Paragraph({ text: `Fecha de emisión: ${new Date().toLocaleString()}`, alignment: AlignmentType.CENTER, spacing: { after: 200 } }),
        new Paragraph({ text: '1. KPIs Agroecológicos Globales y Comprobación de Hipótesis', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: kpiRows }),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        ...chartRuns,

        new Paragraph({ text: '4. Comparativa entre Regiones Agroecológicas', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: regionRows }),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        new Paragraph({ text: '5. Top Mejores Configuraciones de Paisaje (Frente de Pareto)', heading: HeadingLevel.HEADING_2 }),
        new Table({ width: { size: 100, type: 'pct' }, rows: paretoRows }),
      ],
    }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `Reporte_Gestion_Agroecologica_${getTimestamp()}.docx`)
}

export function exportManagementReportToExcel(reportData, filters = {}) {
  const wb = XLSX.utils.book_new()
  const kpis = reportData.kpis_agroecologicos || {}

  const wsKpis = XLSX.utils.json_to_sheet([
    { Metrica: 'Fecha de Emisión', Valor: new Date().toLocaleString() },
    { Metrica: 'Filtro Fecha Inicio', Valor: formatFilterDate(filters.fecha_inicio) },
    { Metrica: 'Filtro Fecha Fin', Valor: formatFilterDate(filters.fecha_fin) },
    { Metrica: 'Filtro Región', Valor: filters.region || 'Todas' },
    { Metrica: 'Total Simulaciones Evaluadas', Valor: kpis.total_simulaciones ?? 0 },
    { Metrica: 'Rendimiento Promedio Base', Valor: kpis.rendimiento_promedio_base ?? 0 },
    { Metrica: 'Rendimiento Promedio Óptimo', Valor: kpis.rendimiento_promedio_optimo ?? 0 },
    { Metrica: 'Delta Rendimiento Promedio', Valor: kpis.delta_rendimiento_promedio ?? 0 },
    { Metrica: 'Delta Rendimiento (%)', Valor: `${formatVal(kpis.delta_rendimiento_pct, 1)}%` },
    { Metrica: 'Abundancia Polinizadores Base', Valor: kpis.abundancia_polinizadores_base ?? 0 },
    { Metrica: 'Abundancia Polinizadores Óptima', Valor: kpis.abundancia_polinizadores_optima ?? 0 },
    { Metrica: 'Delta Abundancia Promedio', Valor: kpis.delta_abundancia_promedio ?? 0 },
    { Metrica: 'Delta Abundancia (%)', Valor: `${formatVal(kpis.delta_abundancia_pct, 1)}%` },
    { Metrica: 'Diversidad Polinizadores Base', Valor: kpis.diversidad_polinizadores_base ?? 0 },
    { Metrica: 'Diversidad Polinizadores Óptima', Valor: kpis.diversidad_polinizadores_optima ?? 0 },
    { Metrica: 'Delta Diversidad Promedio', Valor: kpis.delta_diversidad_promedio ?? 0 },
    { Metrica: 'Tasa Cumplimiento Hipótesis (%)', Valor: `${formatVal(kpis.tasa_cumplimiento_hipotesis, 1)}%` },
    { Metrica: 'Simulaciones que Cumplen Hipótesis', Valor: kpis.simulaciones_cumplen_hipotesis ?? 0 },
    { Metrica: 'Simulaciones que No Cumplen', Valor: kpis.simulaciones_no_cumplen ?? 0 },
  ])
  wsKpis['!cols'] = [{ wch: 38 }, { wch: 35 }]
  XLSX.utils.book_append_sheet(wb, wsKpis, 'KPIs_Agroecologicos')

  const wsReg = XLSX.utils.json_to_sheet((reportData.comparacion_regiones || []).map((cr) => ({
    Region: cr.region,
    Total_Simulaciones: cr.total_simulaciones,
    Rendimiento_Base: cr.rendimiento_promedio_base,
    Rendimiento_Optimo: cr.rendimiento_promedio_optimo,
    Abundancia_Base: cr.abundancia_promedio_base,
    Abundancia_Optima: cr.abundancia_promedio_optimo,
    Diversidad_Base: cr.diversidad_promedio_base,
    Diversidad_Optima: cr.diversidad_promedio_optimo,
    Tasa_Hipotesis: `${formatVal(cr.tasa_cumplimiento_hipotesis, 1)}%`,
  })))
  wsReg['!cols'] = [{ wch: 28 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 16 }, { wch: 16 }, { wch: 16 }]
  XLSX.utils.book_append_sheet(wb, wsReg, 'Comparacion_Regional')

  const wsEvol = XLSX.utils.json_to_sheet((reportData.evolucion_temporal || []).map((et) => ({
    Fecha: et.fecha,
    Rendimiento_Base: et.rendimiento_base,
    Rendimiento_Optimo: et.rendimiento_optimo,
    Delta_Rendimiento: et.delta_rendimiento,
    Abundancia_Base: et.abundancia_base,
    Abundancia_Optima: et.abundancia_optima,
    Delta_Abundancia: et.delta_abundancia,
    Diversidad_Base: et.diversidad_base,
    Diversidad_Optima: et.diversidad_optima,
  })))
  wsEvol['!cols'] = [{ wch: 15 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 16 }, { wch: 16 }]
  XLSX.utils.book_append_sheet(wb, wsEvol, 'Evolucion_Temporal')

  const wsPareto = XLSX.utils.json_to_sheet((reportData.top_configuraciones_pareto || []).map((p) => ({
    Ranking: p.rank,
    Simulacion_ID: p.simulacion_id,
    Region: p.region,
    Fecha: p.fecha,
    Crop_Yield_Index: p.crop_yield_index,
    Pollinator_Abundance_Index: p.pollinator_abundance_index,
    Pollinator_Diversity_Index: p.pollinator_diversity_index,
    Crop_Area_Pct: `${p.crop_area_pct}%`,
    Natural_Area_Pct: `${p.natural_area_pct}%`,
    Floral_Strips_Pct: `${p.floral_strips_pct}%`,
    Pesticide_Level: p.pesticide_level,
    Soil_Management_Score: p.soil_management_score,
    Score_Agroecologico: p.score,
  })))
  wsPareto['!cols'] = [{ wch: 8 }, { wch: 14 }, { wch: 25 }, { wch: 22 }, { wch: 18 }, { wch: 25 }, { wch: 25 }, { wch: 14 }, { wch: 16 }, { wch: 16 }, { wch: 16 }, { wch: 22 }, { wch: 20 }]
  XLSX.utils.book_append_sheet(wb, wsPareto, 'Top_Frente_Pareto')

  XLSX.writeFile(wb, `Reporte_Gestion_Agroecologica_${getTimestamp()}.xlsx`)
}
