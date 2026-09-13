import * as XLSX from 'xlsx'
import jsPDF from 'jspdf'
import { Document, Packer, Paragraph, Table, TableCell, TableRow, TextRun, HeadingLevel, AlignmentType } from 'docx'
import { saveAs } from 'file-saver'

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const isoString = dateString.endsWith('Z') ? dateString : dateString + 'Z'
  return new Date(isoString).toLocaleString()
}

function formatCoords(geometry) {
  if (!geometry || !geometry.coordinates) return 'Sin definir'
  try {
    const coords = geometry.coordinates.flat(Infinity)
    return `Área de Interés: ${geometry.type} (${Math.floor(coords.length / 2)} vértices capturados)`
  } catch (e) {
    return 'Sin definir'
  }
}

function getObjectEntries(obj) {
  if (!obj) return []
  return Object.entries(obj).map(([k, v]) => ({
    label: k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: typeof v === 'number' ? v.toFixed(4) : String(v)
  }))
}

export function exportSimulationToPdf(simulation) {
  const doc = new jsPDF()
  const margin = 14
  let y = 20

  doc.setFontSize(22)
  doc.setTextColor(16, 185, 129) // Emerald-500
  doc.text('Reporte Profesional de Simulación', margin, y)
  y += 12

  doc.setFontSize(14)
  doc.setTextColor(30, 41, 59) // Slate-800
  doc.text('Datos del Cliente y Simulación', margin, y)
  y += 8

  doc.setFontSize(11)
  doc.setTextColor(71, 85, 105) // Slate-600
  const metaData = [
    `Cliente / Usuario ID: #${simulation.usuario_id ?? 'N/A'}`,
    `Fecha y Hora de Simulación: ${formatDate(simulation.fecha)}`,
    `ID de Simulación (Registro): ${simulation.id ?? 'N/A'}`,
    `Ubicación: ${formatCoords(simulation.coordenadas_geojson)}`,
  ]
  metaData.forEach(text => {
    doc.text(text, margin, y)
    y += 6
  })
  y += 6

  doc.setFontSize(14)
  doc.setTextColor(30, 41, 59)
  doc.text('Condiciones Iniciales (Línea Base)', margin, y)
  y += 8

  doc.setFontSize(11)
  doc.setTextColor(71, 85, 105)
  const baseData = getObjectEntries(simulation.metricas_base)
  baseData.forEach(item => {
    doc.text(`• ${item.label}: ${item.value}`, margin + 4, y)
    y += 6
  })
  y += 6

  doc.setFontSize(14)
  doc.setTextColor(30, 41, 59)
  doc.text('Análisis de Mejoramiento (Posterior)', margin, y)
  y += 8

  doc.setFontSize(11)
  doc.setTextColor(71, 85, 105)
  const optimalData = getObjectEntries(simulation.metricas_optimas)
  optimalData.forEach(item => {
    if (y > 280) { doc.addPage(); y = 20; }
    doc.text(`• ${item.label}: ${item.value}`, margin + 4, y)
    y += 6
  })
  y += 6

  if (simulation.variables_entrada && Object.keys(simulation.variables_entrada).length > 0) {
    if (y > 260) { doc.addPage(); y = 20; }
    doc.setFontSize(14)
    doc.setTextColor(30, 41, 59)
    doc.text('Parámetros de Configuración del Escenario', margin, y)
    y += 8

    doc.setFontSize(11)
    doc.setTextColor(71, 85, 105)
    const inputData = getObjectEntries(simulation.variables_entrada)
    inputData.forEach(item => {
      if (y > 280) { doc.addPage(); y = 20; }
      doc.text(`• ${item.label}: ${item.value}`, margin + 4, y)
      y += 6
    })
  }

  doc.save(`GemeloDigital_Reporte_${simulation.id ?? 'detalle'}.pdf`)
}

export async function exportSimulationToDocx(simulation) {
  const metaData = [
    { label: 'Cliente / Usuario ID', value: `#${simulation.usuario_id ?? 'N/A'}` },
    { label: 'Fecha y Hora', value: formatDate(simulation.fecha) },
    { label: 'ID de Simulación', value: `${simulation.id ?? 'N/A'}` },
    { label: 'Ubicación y Área', value: formatCoords(simulation.coordenadas_geojson) },
  ]
  const baseData = getObjectEntries(simulation.metricas_base)
  const optimalData = getObjectEntries(simulation.metricas_optimas)
  const inputData = getObjectEntries(simulation.variables_entrada)

  const createTable = (data) => new Table({
    width: { size: 100, type: 'pct' },
    rows: [
      new TableRow({ children: [
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: 'Métrica/Atributo', bold: true })] })] }),
        new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: 'Valor Registrado', bold: true })] })] })
      ]}),
      ...data.map(item => new TableRow({ children: [
        new TableCell({ children: [new Paragraph(item.label)] }),
        new TableCell({ children: [new Paragraph(item.value)] })
      ]}))
    ],
  })

  const doc = new Document({
    sections: [{
      properties: {},
      children: [
        new Paragraph({
          text: 'Gemelo Digital de Polinizadores',
          heading: HeadingLevel.TITLE,
          alignment: AlignmentType.CENTER,
        }),
        new Paragraph({
          text: 'Reporte Profesional de Simulación de Mejoramiento de Paisaje',
          heading: HeadingLevel.HEADING_1,
          alignment: AlignmentType.CENTER,
        }),
        new Paragraph({ text: '', spacing: { after: 200 } }),
        
        new Paragraph({ text: '1. Datos Generales de la Simulación', heading: HeadingLevel.HEADING_2 }),
        createTable(metaData),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        new Paragraph({ text: '2. Condiciones Iniciales (Línea Base)', heading: HeadingLevel.HEADING_2 }),
        createTable(baseData),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        new Paragraph({ text: '3. Análisis de Mejoramiento (Posterior)', heading: HeadingLevel.HEADING_2 }),
        createTable(optimalData),
        new Paragraph({ text: '', spacing: { after: 200 } }),

        new Paragraph({ text: '4. Parámetros de Configuración del Escenario', heading: HeadingLevel.HEADING_2 }),
        createTable(inputData),
      ],
    }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `GemeloDigital_Reporte_${simulation.id ?? 'detalle'}.docx`)
}

export function exportSimulationToExcel(simulation) {
  const metaData = [
    { Categoria: 'Metadatos Generales', Metrica: 'Cliente / Usuario ID', Valor: `#${simulation.usuario_id ?? 'N/A'}` },
    { Categoria: 'Metadatos Generales', Metrica: 'Fecha y Hora', Valor: formatDate(simulation.fecha) },
    { Categoria: 'Metadatos Generales', Metrica: 'ID de Simulación', Valor: simulation.id ?? 'N/A' },
    { Categoria: 'Metadatos Generales', Metrica: 'Ubicación y Área', Valor: formatCoords(simulation.coordenadas_geojson) },
  ]
  const baseData = getObjectEntries(simulation.metricas_base).map(i => ({ Categoria: 'Condiciones Iniciales (Línea Base)', Metrica: i.label, Valor: i.value }))
  const optimalData = getObjectEntries(simulation.metricas_optimas).map(i => ({ Categoria: 'Análisis de Mejoramiento (Posterior)', Metrica: i.label, Valor: i.value }))
  const inputData = getObjectEntries(simulation.variables_entrada).map(i => ({ Categoria: 'Parámetros Configuración Escenario', Metrica: i.label, Valor: i.value }))

  const allData = [...metaData, ...baseData, ...optimalData, ...inputData]

  const worksheet = XLSX.utils.json_to_sheet(allData);
  
  // Set column widths for better readability
  worksheet['!cols'] = [
    { wch: 45 },
    { wch: 35 },
    { wch: 40 }
  ];

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Reporte_Mejoramiento");
  
  XLSX.writeFile(workbook, `GemeloDigital_Reporte_${simulation.id ?? 'detalle'}.xlsx`);
}
