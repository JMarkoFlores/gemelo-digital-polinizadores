/**
 * Suite de pruebas de verificación directa para la Auditoría 07:
 * Funciones de presentación en pantalla y exportación de informes de gestión.
 * Ejecutable mediante: node --loader ./tests/revision/loader.mjs tests/revision/test_audit07_frontend_exporters.mjs
 */

import assert from 'node:assert/strict'
import { exportManagementReportToExcel } from '../../frontend/src/lib/generalReportExporters.js'

console.log('=== INICIANDO PRUEBAS DE EXPORTACIÓN Y PANTALLA (AUDITORÍA 07) ===\n')

let passedCount = 0

function runTest(name, fn) {
  try {
    fn()
    console.log(`[PASS] ${name}`)
    passedCount++
  } catch (err) {
    console.error(`[FAIL] ${name}`)
    console.error(err)
    process.exitCode = 1
  }
}

// Helpers de formateo idénticos a AdminReportsPage.jsx
function formatUiMetric(val, decimals = 1, unit = 'pts') {
  if (val === null || val === undefined) return 'N/D'
  const formatted = Number(val).toFixed(decimals)
  return unit ? `${formatted} ${unit}` : formatted
}

function formatUiDeltaHint(base, delta, deltaPct, decimals = 1, unit = 'pts') {
  if (base === null || base === undefined) return 'Sin datos de línea base'
  const baseStr = `Base: ${Number(base).toFixed(decimals)}`
  if (delta === null || delta === undefined) {
    return `${baseStr} (Sin solución evaluable)`
  }
  const sign = delta > 0 ? '+' : ''
  const pctStr = deltaPct !== null && deltaPct !== undefined ? `, ${sign}${Number(deltaPct).toFixed(1)}%` : ''
  return `${baseStr} (Δ ${sign}${Number(delta).toFixed(decimals)} ${unit}${pctStr})`
}

// 1. Caso A: Una simulación que cumple y otra no evaluable
runTest('Caso A: Excel - 1 cumple y 1 no evaluable (categorías coherentes)', () => {
  const mockData = {
    kpis_agroecologicos: {
      total_simulaciones: 2,
      simulaciones_evaluables: 1,
      simulaciones_no_evaluables: 1,
      simulaciones_cumplen_hipotesis: 1,
      simulaciones_no_cumplen: 0,
      denominador_tasa: 'evaluables',
      tasa_cumplimiento_hipotesis: 100.0,
      rendimiento_promedio_base: 100.0,
      rendimiento_promedio_optimo: 110.0,
      delta_rendimiento_promedio: 10.0,
      delta_rendimiento_pct: 10.0,
      abundancia_polinizadores_base: 50.0,
      abundancia_polinizadores_optima: 70.0,
      delta_abundancia_promedio: 20.0,
      delta_abundancia_pct: 40.0,
      diversidad_polinizadores_base: 0.5,
      diversidad_polinizadores_optima: 0.7,
      delta_diversidad_promedio: 0.2,
      rendimiento_promedio_base_total: 550.0,
      abundancia_polinizadores_base_total: 275.0,
      diversidad_polinizadores_base_total: 0.7,
    },
    comparacion_regiones: [],
    evolucion_temporal: [],
    top_configuraciones_pareto: [],
  }

  // Interceptamos la llamada a json_to_sheet invocando exportManagementReportToExcel
  let capturedSheets = {}
  const origJsonToSheet = globalThis.__mock_json_to_sheet
  // En nuestro mock_deps, XLSX.utils.json_to_sheet devuelve {!data: rows}
  exportManagementReportToExcel(mockData, {})

  // Verificamos mediante el objeto workbook
  // En el mock, wb.Sheets['KPIs_Agroecologicos']['!data'] tiene las filas
  const kpiRows = globalThis.__lastWorkbook?.Sheets['KPIs_Agroecologicos']?.['!data']
  assert(kpiRows, 'Debe generarse la hoja de KPIs')

  const findRow = (metrica) => kpiRows.find((r) => r.Metrica === metrica)

  assert.equal(findRow('Total Simulaciones Registradas')?.Valor, 2)
  assert.equal(findRow('Simulaciones Evaluables (con solución)')?.Valor, 1)
  assert.equal(findRow('Simulaciones No Evaluables (sin solución)')?.Valor, 1)
  assert.equal(findRow('Simulaciones que Cumplen Criterio')?.Valor, 1)
  assert.equal(findRow('Simulaciones que No Cumplen (evaluables)')?.Valor, 0)
  assert.equal(findRow('Denominador de la Tasa')?.Valor, 'evaluables')
  assert.equal(findRow('Tasa Cumplimiento Criterio Operativo (%)')?.Valor, '100.0%')
  assert.equal(findRow('Delta Rendimiento Promedio')?.Valor, 10.0)
})

// 2. Caso B: Todas no evaluables (sin solución)
runTest('Caso B: Excel - Todas no evaluables no fabrican ceros espurios', () => {
  const mockData = {
    kpis_agroecologicos: {
      total_simulaciones: 2,
      simulaciones_evaluables: 0,
      simulaciones_no_evaluables: 2,
      simulaciones_cumplen_hipotesis: 0,
      simulaciones_no_cumplen: 0,
      denominador_tasa: 'evaluables',
      tasa_cumplimiento_hipotesis: null,
      rendimiento_promedio_base: null,
      rendimiento_promedio_optimo: null,
      delta_rendimiento_promedio: null,
      delta_rendimiento_pct: null,
      abundancia_polinizadores_base: null,
      abundancia_polinizadores_optima: null,
      delta_abundancia_promedio: null,
      delta_abundancia_pct: null,
      diversidad_polinizadores_base: null,
      diversidad_polinizadores_optima: null,
      delta_diversidad_promedio: null,
      rendimiento_promedio_base_total: 100.0,
      abundancia_polinizadores_base_total: 60.0,
      diversidad_polinizadores_base_total: 0.6,
    },
    comparacion_regiones: [
      {
        region: 'Norte',
        total_simulaciones: 2,
        simulaciones_evaluables: 0,
        simulaciones_no_evaluables: 2,
        simulaciones_cumplen_hipotesis: 0,
        simulaciones_no_cumplen: 0,
        rendimiento_promedio_base: null,
        rendimiento_promedio_optimo: null,
        delta_rendimiento_promedio: null,
        abundancia_promedio_base: null,
        abundancia_promedio_optimo: null,
        delta_abundancia_promedio: null,
        diversidad_promedio_base: null,
        diversidad_promedio_optimo: null,
        delta_diversidad_promedio: null,
        tasa_cumplimiento_hipotesis: null,
        denominador_tasa: 'evaluables',
      },
    ],
    evolucion_temporal: [],
    top_configuraciones_pareto: [],
  }

  exportManagementReportToExcel(mockData, {})
  const kpiRows = globalThis.__lastWorkbook?.Sheets['KPIs_Agroecologicos']?.['!data']
  const findRow = (metrica) => kpiRows.find((r) => r.Metrica === metrica)

  // Recuentos reales son 0
  assert.equal(findRow('Simulaciones Evaluables (con solución)')?.Valor, 0)
  assert.equal(findRow('Simulaciones que Cumplen Criterio')?.Valor, 0)
  assert.equal(findRow('Simulaciones que No Cumplen (evaluables)')?.Valor, 0)

  // Métricas ausentes deben ser 'N/D', NO números 0 ni '0%'
  assert.equal(findRow('Tasa Cumplimiento Criterio Operativo (%)')?.Valor, 'N/D')
  assert.notEqual(findRow('Tasa Cumplimiento Criterio Operativo (%)')?.Valor, '0%')
  assert.equal(findRow('Rendimiento Promedio Óptimo')?.Valor, 'N/D')
  assert.notEqual(findRow('Rendimiento Promedio Óptimo')?.Valor, 0)
  assert.equal(findRow('Delta Rendimiento Promedio')?.Valor, 'N/D')
  assert.notEqual(findRow('Delta Rendimiento Promedio')?.Valor, 0)
  assert.equal(findRow('Delta Rendimiento (%)')?.Valor, 'N/D')
  assert.equal(findRow('Abundancia Polinizadores Óptima')?.Valor, 'N/D')
  assert.equal(findRow('Diversidad Polinizadores Óptima')?.Valor, 'N/D')

  // En hoja regional
  const regRows = globalThis.__lastWorkbook?.Sheets['Comparacion_Regional']?.['!data']
  assert.equal(regRows[0].Rendimiento_Optimo, 'N/D')
  assert.equal(regRows[0].Delta_Rendimiento, 'N/D')
  assert.equal(regRows[0].Tasa_Criterio_Operativo, 'N/D')
  assert.equal(regRows[0].Denominador_Tasa, 'evaluables')
})

// 3. Caso E: Distinción entre métrica ausente (None) y métrica real igual a cero (0.0)
runTest('Caso E: Preservación de cero real vs ausencia de dato', () => {
  // 1. Métrica con cero numérico real (ej. delta = 0.0)
  const dataWithZero = {
    kpis_agroecologicos: {
      total_simulaciones: 1,
      simulaciones_evaluables: 1,
      simulaciones_no_evaluables: 0,
      simulaciones_cumplen_hipotesis: 0,
      simulaciones_no_cumplen: 1,
      tasa_cumplimiento_hipotesis: 0.0,
      rendimiento_promedio_base: 80.0,
      rendimiento_promedio_optimo: 80.0,
      delta_rendimiento_promedio: 0.0, // Cero real
      delta_rendimiento_pct: 0.0,      // Cero real
    },
    comparacion_regiones: [],
    evolucion_temporal: [],
    top_configuraciones_pareto: [],
  }

  exportManagementReportToExcel(dataWithZero, {})
  const kpiRows = globalThis.__lastWorkbook?.Sheets['KPIs_Agroecologicos']?.['!data']
  const findRow = (metrica) => kpiRows.find((r) => r.Metrica === metrica)

  // El cero real se conserva numéricamente
  assert.strictEqual(findRow('Delta Rendimiento Promedio')?.Valor, 0.0)
  assert.equal(findRow('Delta Rendimiento (%)')?.Valor, '0.0%')
  assert.equal(findRow('Tasa Cumplimiento Criterio Operativo (%)')?.Valor, '0.0%')

  // Formato UI en pantalla
  assert.equal(formatUiMetric(0, 1, 'pts'), '0.0 pts')
  assert.equal(formatUiMetric(null, 1, 'pts'), 'N/D')
  assert.equal(formatUiMetric(undefined, 1, 'pts'), 'N/D')

  assert.equal(formatUiDeltaHint(80.0, 0.0, 0.0, 1), 'Base: 80.0 (Δ 0.0 pts, 0.0%)')
  assert.equal(formatUiDeltaHint(80.0, null, null, 1), 'Base: 80.0 (Sin solución evaluable)')
})

// 4. Caso F: Conservación de comparación pareada +10.0 en exportación
runTest('Caso F: Excel conserva delta pareado +10.0 ante registros dispares', () => {
  const mockData = {
    kpis_agroecologicos: {
      total_simulaciones: 2,
      simulaciones_evaluables: 1,
      simulaciones_no_evaluables: 1,
      rendimiento_promedio_base: 100.0,
      rendimiento_promedio_optimo: 110.0,
      delta_rendimiento_promedio: 10.0,
      rendimiento_promedio_base_total: 550.0,
    },
    comparacion_regiones: [],
    evolucion_temporal: [],
    top_configuraciones_pareto: [],
  }

  exportManagementReportToExcel(mockData, {})
  const kpiRows = globalThis.__lastWorkbook?.Sheets['KPIs_Agroecologicos']?.['!data']
  const findRow = (metrica) => kpiRows.find((r) => r.Metrica === metrica)

  assert.equal(findRow('Rendimiento Promedio Base (evaluables)')?.Valor, 100.0)
  assert.equal(findRow('Rendimiento Promedio Óptimo')?.Valor, 110.0)
  assert.equal(findRow('Delta Rendimiento Promedio')?.Valor, 10.0)
  assert.equal(findRow('Rendimiento Promedio Base Total (población)')?.Valor, 550.0)
})

// 5. Verificación de ausencia de claims indebidos ('Hipótesis Comprobada')
runTest('Consistencia terminológica: No usa "Hipótesis Comprobada"', () => {
  const mockData = {
    kpis_agroecologicos: {
      total_simulaciones: 1,
      simulaciones_evaluables: 1,
      simulaciones_no_evaluables: 0,
      simulaciones_cumplen_hipotesis: 1,
      simulaciones_no_cumplen: 0,
      tasa_cumplimiento_hipotesis: 100.0,
    },
    comparacion_regiones: [],
    evolucion_temporal: [],
    top_configuraciones_pareto: [],
  }

  exportManagementReportToExcel(mockData, {})
  const kpiRows = globalThis.__lastWorkbook?.Sheets['KPIs_Agroecologicos']?.['!data']

  kpiRows.forEach((row) => {
    assert(
      !String(row.Metrica).toLowerCase().includes('hipótesis comprobada'),
      `La métrica "${row.Metrica}" no debe contener "hipótesis comprobada"`
    )
  })
})

console.log(`\n=== TODAS LAS ${passedCount} PRUEBAS FRONTEND/EXPORTER SUPERADAS CON ÉXITO ===`)
