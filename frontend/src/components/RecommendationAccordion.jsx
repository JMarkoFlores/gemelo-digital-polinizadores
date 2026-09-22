import { useState, useMemo } from 'react'

/**
 * Renderiza fragmentos de texto inline procesando negritas en Markdown (**texto** o __texto__).
 */
function renderFormattedInline(text) {
  if (!text) return null
  const parts = text.split(/(\*\*.*?\*\*|__.*?__)/g)
  return parts.map((part, index) => {
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      return (
        <strong
          key={index}
          className="font-bold text-slate-900 dark:text-slate-100 bg-emerald-500/10 dark:bg-emerald-500/20 px-1 py-0.5 rounded text-emerald-950 dark:text-emerald-200"
        >
          {part.slice(2, -2)}
        </strong>
      )
    }
    return <span key={index}>{part}</span>
  })
}

/**
 * Parsea el texto devuelto por Langflow/Groq/Heurística en sub-secciones estructuradas.
 */
function parseSections(text) {
  if (!text) return []

  // Dividir por doble salto de línea
  let rawBlocks = text
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean)

  // Si solo hay un bloque pero contiene saltos de línea y viñetas/números, dividir por salto simple
  if (
    rawBlocks.length === 1 &&
    text.includes('\n') &&
    /(?:^\d+[\.)]|^\*|^-)\s+/m.test(text)
  ) {
    rawBlocks = text.split(/\n+/).map((b) => b.trim()).filter(Boolean)
  }

  return rawBlocks.map((block, idx) => {
    let title = null
    let body = block

    // Caso 1: Encabezado Markdown (### Título)
    const hMatch = body.match(/^#{1,4}\s+([^\n]+)\n*([\s\S]*)$/)
    if (hMatch) {
      title = hMatch[1].trim()
      body = hMatch[2].trim()
    } else {
      // Caso 2: Título en negrita al inicio (**Título:** o **Título**:)
      const boldHeaderMatch = body.match(
        /^(?:(?:\d+[\.)]|\*|-)\s*)?\*\*([^*]+)\*\*:?\s*([\s\S]+)$/
      )
      if (boldHeaderMatch) {
        title = boldHeaderMatch[1].trim().replace(/:$/, '')
        body = boldHeaderMatch[2].trim()
      } else {
        // Caso 3: Título numerado con dos puntos (ej: 1. MOTIVO DEL COMPROMISO: cuerpo)
        const numHeaderMatch = body.match(
          /^(?:(?:\d+[\.)]|\*|-)\s*)?([A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s()/\-–—]{3,55}?):\s*([\s\S]+)$/
        )
        if (numHeaderMatch) {
          title = numHeaderMatch[1].trim()
          body = numHeaderMatch[2].trim()
        }
      }
    }

    // Título semántico de respaldo si el bloque no tenía encabezado explícito
    if (!title) {
      const lower = block.toLowerCase()
      if (
        lower.includes('recomendación') ||
        lower.includes('en campo') ||
        lower.includes('acciones') ||
        lower.includes('operativa')
      ) {
        title = 'Recomendación Operativa en Campo'
      } else if (
        lower.includes('factores') ||
        lower.includes('determinantes') ||
        lower.includes('variables clave') ||
        lower.includes('pesticidas')
      ) {
        title = 'Factores Determinantes y Variables Clave'
      } else if (idx === 0) {
        title = 'Motivo de Selección y Trade-offs'
      } else {
        title = `Aspecto Agroecológico ${idx + 1}`
      }
    }

    return { title, body }
  })
}

/**
 * Devuelve un ícono contextual según el título de la sub-sección.
 */
function getSectionIcon(title) {
  const t = (title || '').toLowerCase()
  if (
    t.includes('motivo') ||
    t.includes('trade-off') ||
    t.includes('compromiso') ||
    t.includes('selección')
  ) {
    return (
      <svg
        className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
        />
      </svg>
    )
  }
  if (
    t.includes('factores') ||
    t.includes('variables') ||
    t.includes('determinantes') ||
    t.includes('pesticidas')
  ) {
    return (
      <svg
        className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    )
  }
  if (
    t.includes('campo') ||
    t.includes('recomendación') ||
    t.includes('operativa') ||
    t.includes('acción')
  ) {
    return (
      <svg
        className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
    )
  }
  return (
    <svg
      className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

/**
 * Renderiza el cuerpo de una sección soportando listas numeradas, viñetas y párrafos.
 */
function renderSectionBody(body) {
  if (!body) return null

  const lines = body
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)

  const isNumbered = lines.length > 1 && lines.every((l) => /^\d+[\.)]\s+/.test(l))
  const isBullet = lines.length > 1 && lines.every((l) => /^[-*•]\s+/.test(l))

  if (isNumbered) {
    return (
      <ol className="list-decimal list-inside space-y-1.5 text-slate-700 dark:text-slate-300 text-xs sm:text-sm leading-relaxed">
        {lines.map((line, idx) => (
          <li key={idx} className="pl-1">
            {renderFormattedInline(line.replace(/^\d+[\.)]\s+/, ''))}
          </li>
        ))}
      </ol>
    )
  }

  if (isBullet) {
    return (
      <ul className="list-disc list-inside space-y-1.5 text-slate-700 dark:text-slate-300 text-xs sm:text-sm leading-relaxed">
        {lines.map((line, idx) => (
          <li key={idx} className="pl-1">
            {renderFormattedInline(line.replace(/^[-*•]\s+/, ''))}
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="space-y-2 text-slate-700 dark:text-slate-300 text-xs sm:text-sm leading-relaxed">
      {lines.map((line, idx) => (
        <p key={idx}>{renderFormattedInline(line)}</p>
      ))}
    </div>
  )
}

/**
 * Componente acordeón colapsable con animación fluida y parseo de markdown para la recomendación IA de Langflow.
 */
export default function RecommendationAccordion({ rawReason, isAiGenerated }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const sections = useMemo(() => parseSections(rawReason), [rawReason])

  return (
    <div className="mt-3 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/[0.06] via-teal-500/[0.04] to-transparent p-3.5 sm:p-4 shadow-xs transition-all duration-300 dark:border-emerald-500/40 dark:bg-slate-950/70">
      {/* Botón Encabezado para expandir/colapsar */}
      <button
        type="button"
        id="btn-toggle-recommendation-accordion"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
        className="group flex w-full items-center justify-between gap-2.5 text-left focus:outline-hidden cursor-pointer select-none"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-emerald-900 dark:text-emerald-300 text-xs sm:text-sm flex items-center gap-1.5">
            <svg
              className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />
            </svg>
            ✦ Motivo de selección y trade-offs:
          </span>
          {isAiGenerated ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Recomendación IA (Langflow)
            </span>
          ) : (
            <span className="text-[10px] text-slate-400 font-medium">Heurística NSGA-II</span>
          )}
        </div>

        {/* Indicador de acción interactiva */}
        <div className="flex items-center gap-1.5 shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 group-hover:bg-emerald-500/20 transition-colors">
          <span className="hidden sm:inline font-medium">
            {isExpanded ? 'Ocultar análisis' : 'Ver análisis completo'}
          </span>
          <svg
            className={`w-4 h-4 transform transition-transform duration-300 ${
              isExpanded ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Contenedor expandible con transición suave en altura */}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-in-out ${
          isExpanded
            ? 'grid-rows-[1fr] opacity-100 mt-3 pt-3 border-t border-emerald-500/20 dark:border-emerald-500/30'
            : 'grid-rows-[0fr] opacity-0'
        }`}
      >
        <div className="overflow-hidden space-y-3">
          {sections.map((section, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-emerald-500/15 bg-white/70 p-3.5 shadow-2xs dark:border-emerald-500/20 dark:bg-slate-900/60 transition-all"
            >
              <div className="flex items-center gap-2 mb-1.5">
                {getSectionIcon(section.title)}
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300 font-display">
                  {section.title}
                </h4>
              </div>
              {renderSectionBody(section.body)}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
