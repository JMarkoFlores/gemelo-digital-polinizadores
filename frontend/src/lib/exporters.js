import jsPDF from 'jspdf'
import { Document, Packer, Paragraph, Table, TableCell, TableRow, TextRun } from 'docx'
import { saveAs } from 'file-saver'

export function exportSimulationToPdf(simulation) {
  const doc = new jsPDF()
  doc.setFontSize(18)
  doc.text('Reporte de simulacion', 14, 20)
  doc.setFontSize(11)
  doc.text(`ID: ${simulation.id ?? 'N/A'}`, 14, 30)
  doc.text(`Fecha: ${simulation.fecha ?? 'N/A'}`, 14, 38)
  doc.text(`Hipotesis: ${simulation.metricas_optimas?.selection_reason || simulation.hypothesis_status || 'N/A'}`, 14, 46)
  const rows = [
    ['Rendimiento base', String(simulation.metricas_base?.crop_yield_index ?? simulation.metricas_base?.rendimiento ?? 'N/A')],
    ['Polinizadores base', String(simulation.metricas_base?.pollinator_abundance_index ?? simulation.metricas_base?.polinizadores ?? 'N/A')],
    ['Rendimiento optimo', String(simulation.metricas_optimas?.crop_yield_index ?? simulation.metricas_optimas?.rendimiento ?? 'N/A')],
    ['Polinizadores optimo', String(simulation.metricas_optimas?.pollinator_abundance_index ?? simulation.metricas_optimas?.polinizadores ?? 'N/A')],
  ]
  let y = 60
  rows.forEach(([label, value]) => {
    doc.text(`${label}: ${value}`, 14, y)
    y += 8
  })
  doc.save(`simulacion-${simulation.id ?? 'detalle'}.pdf`)
}

export async function exportSimulationReportToDocx(payload) {
  const simulation = payload.simulation
  const user = payload.user
  const doc = new Document({
    sections: [
      {
        children: [
          new Paragraph({ children: [new TextRun({ text: 'Reporte de simulacion', bold: true, size: 32 })] }),
          new Paragraph(`Usuario: ${user.email}`),
          new Paragraph(`Fecha: ${simulation.fecha}`),
          new Table({
            rows: [
              new TableRow({ children: [new TableCell({ children: [new Paragraph('Campo')] }), new TableCell({ children: [new Paragraph('Valor')] })] }),
              new TableRow({ children: [new TableCell({ children: [new Paragraph('Rendimiento base')] }), new TableCell({ children: [new Paragraph(String(simulation.metricas_base?.crop_yield_index ?? 'N/A'))] })] }),
              new TableRow({ children: [new TableCell({ children: [new Paragraph('Polinizadores base')] }), new TableCell({ children: [new Paragraph(String(simulation.metricas_base?.pollinator_abundance_index ?? 'N/A'))] })] }),
              new TableRow({ children: [new TableCell({ children: [new Paragraph('Rendimiento optimo')] }), new TableCell({ children: [new Paragraph(String(simulation.metricas_optimas?.crop_yield_index ?? 'N/A'))] })] }),
              new TableRow({ children: [new TableCell({ children: [new Paragraph('Polinizadores optimo')] }), new TableCell({ children: [new Paragraph(String(simulation.metricas_optimas?.pollinator_abundance_index ?? 'N/A'))] })] }),
            ],
          }),
        ],
      },
    ],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `simulacion-${simulation.id}.docx`)
}
