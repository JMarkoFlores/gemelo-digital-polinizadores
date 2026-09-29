import React from 'react'
import { LAND_USE_PALETTE } from '../lib/landUseColors'

/**
 * Anillo de progreso circular SVG (donut chart) para la tarjeta 2D (Mockup 1)
 */
export function CircularProgressRing({
  percentage = 0,
  size = 46,
  strokeWidth = 4.2,
  color = '#38bdf8',
  trackColor = 'currentColor',
}) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const validPct = Math.max(0, Math.min(100, Number(percentage) || 0))
  const offset = circumference - (validPct / 100) * circumference

  return (
    <div
      className="relative inline-flex items-center justify-center shrink-0 select-none"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke={trackColor}
          strokeWidth={strokeWidth}
          className="text-slate-200 dark:text-slate-800/80"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[10px] sm:text-[11px] font-bold font-mono text-slate-800 dark:text-slate-100">
        {validPct.toFixed(1)}%
      </span>
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
   ICONOS VECTORIALES ESTILIZADOS
   ────────────────────────────────────────────────────────────────────────── */

// 🍃 Hoja botánica para Cultivo (2D - Mockup 1)
export function LeafIcon({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none">
      {/* Silueta de hoja con relleno translúcido verde y nervadura */}
      <path
        d="M26 6C20 6 12 9 8 16c-3 5.2-1.5 9 1 10 2.5 1 6.5 0 11-4 6-5.5 8-13 6-16Z"
        fill="#34d399"
        fillOpacity="0.85"
        stroke="#065f46"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M6 26c3-3 8-7 13-11"
        stroke="#065f46"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M13 19l3-1M16 15l3-1M11 22l2-1"
        stroke="#065f46"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

// 🌳 Árbol y montaña para Seminatural (2D - Mockup 1)
export function ForestMountainIcon({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none">
      {/* Nube superior suave */}
      <path
        d="M19 8a2.5 2.5 0 0 1 4.5.5A2 2 0 0 1 24.5 12H18a2 2 0 0 1 1-4Z"
        fill="#94a3b8"
        fillOpacity="0.55"
      />
      {/* Montaña de fondo */}
      <path
        d="M13 24l6-11 6.5 11H13Z"
        fill="#64748b"
        stroke="#334155"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Cima nevada */}
      <path
        d="M19 13l2.2 4-1.2 1-1.5-1.5-1 1.5L19 13Z"
        fill="#f8fafc"
      />
      {/* Tronco de árbol */}
      <rect x="9.5" y="19" width="3" height="5" rx="1" fill="#78350f" stroke="#451a03" strokeWidth="1.2" />
      {/* Copa del árbol */}
      <path
        d="M11 9c-3.5 0-6 2.5-6 5.5 0 2 1.2 3.8 3 4.5h6c1.8-.7 3-2.5 3-4.5 0-3-2.5-5.5-6-5.5Z"
        fill="#22c55e"
        stroke="#15803d"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Línea de base */}
      <path d="M4 25h24" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

// 🌸 Ramillete floral para Franjas Florales (2D - Mockup 1)
export function BouquetIcon({ className = 'w-6 h-6' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none">
      {/* Tallos verdes */}
      <path d="M16 19v7M12 16l4 7M20 16l-4 7" stroke="#15803d" strokeWidth="1.6" strokeLinecap="round" />
      {/* Hojas laterales */}
      <path d="M13 21c-1.5-.5-2.5-1.8-2.5-3" stroke="#22c55e" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M19 21c1.5-.5 2.5-1.8 2.5-3" stroke="#22c55e" strokeWidth="1.4" strokeLinecap="round" />
      {/* Flor central superior */}
      <circle cx="16" cy="11" r="2.2" fill="#fbbf24" stroke="#d97706" strokeWidth="1" />
      <circle cx="16" cy="7.5" r="1.8" fill="#f472b6" />
      <circle cx="16" cy="14.5" r="1.8" fill="#f472b6" />
      <circle cx="12.5" cy="11" r="1.8" fill="#f472b6" />
      <circle cx="19.5" cy="11" r="1.8" fill="#f472b6" />
      {/* Flor izquierda */}
      <circle cx="10" cy="16" r="1.8" fill="#f59e0b" stroke="#b45309" strokeWidth="0.8" />
      <circle cx="10" cy="13.2" r="1.4" fill="#fb7185" />
      <circle cx="10" cy="18.8" r="1.4" fill="#fb7185" />
      <circle cx="7.2" cy="16" r="1.4" fill="#fb7185" />
      <circle cx="12.8" cy="16" r="1.4" fill="#fb7185" />
      {/* Flor derecha */}
      <circle cx="22" cy="16" r="1.8" fill="#f59e0b" stroke="#b45309" strokeWidth="0.8" />
      <circle cx="22" cy="13.2" r="1.4" fill="#fb7185" />
      <circle cx="22" cy="18.8" r="1.4" fill="#fb7185" />
      <circle cx="19.2" cy="16" r="1.4" fill="#fb7185" />
      <circle cx="24.8" cy="16" r="1.4" fill="#fb7185" />
    </svg>
  )
}

// 🌾 Espigas de trigo simétricas para Cultivo (3D - Mockup 0)
export function Wheat3DIcon({ className = 'w-7 h-7', color = 'currentColor' }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
      {/* Tallo central */}
      <path d="M16 28V6" />
      {/* Granos tallo central */}
      <path d="M16 7c-2.2-.4-3.5-2-3.5-3.5 2.2.4 3.5 2 3.5 3.5Z" />
      <path d="M16 7c2.2-.4 3.5-2 3.5-3.5-2.2.4-3.5 2-3.5 3.5Z" />
      <path d="M16 11c-2.5-.5-4-2.2-4-4 2.5.5 4 2.2 4 4Z" />
      <path d="M16 11c2.5-.5 4-2.2 4-4-2.5.5-4 2.2-4 4Z" />
      <path d="M16 15c-2.5-.5-4-2.2-4-4 2.5.5 4 2.2 4 4Z" />
      <path d="M16 15c2.5-.5 4-2.2 4-4-2.5.5-4 2.2-4 4Z" />
      <path d="M16 19c-2.2-.5-3.5-2-3.5-3.5 2.2.5 3.5 2 3.5 3.5Z" />
      <path d="M16 19c2.2-.5 3.5-2 3.5-3.5-2.2.5-3.5 2-3.5 3.5Z" />

      {/* Espiga izquierda curvada */}
      <path d="M16 27c-3-4-6-10-6-17" />
      <path d="M10 11c-2-.3-3.2-1.8-3.2-3.2 2 .3 3.2 1.8 3.2 3.2Z" />
      <path d="M10.8 14c-2-.4-3.2-1.8-3.2-3.2 2 .4 3.2 1.8 3.2 3.2Z" />
      <path d="M11.8 17c-2-.4-3-1.8-3-3 2 .4 3 1.8 3 3Z" />

      {/* Espiga derecha curvada */}
      <path d="M16 27c3-4 6-10 6-17" />
      <path d="M22 11c2-.3 3.2-1.8 3.2-3.2-2 .3-3.2 1.8-3.2 3.2Z" />
      <path d="M21.2 14c2-.4 3.2-1.8 3.2-3.2-2 .4-3.2 1.8-3.2 3.2Z" />
      <path d="M20.2 17c2-.4 3-1.8 3-3-2 .4-3 1.8-3 3Z" />
    </svg>
  )
}

// 🕸️ Red ecológica / mandala de nodos para Seminatural (3D - Mockup 0)
export function EcologyNetworkIcon({ className = 'w-7 h-7', color = 'currentColor' }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className}>
      {/* Círculo central */}
      <circle cx="16" cy="16" r="3.2" strokeWidth="1.8" />
      <circle cx="16" cy="16" r="1.2" fill={color} />
      {/* Anillo concéntrico discontinuo */}
      <circle cx="16" cy="16" r="6.5" strokeDasharray="2 3" />
      {/* Nodos cardinales */}
      <circle cx="16" cy="7" r="1.8" />
      <circle cx="25" cy="16" r="1.8" />
      <circle cx="16" cy="25" r="1.8" />
      <circle cx="7" cy="16" r="1.8" />
      {/* Nodos diagonales */}
      <circle cx="22.5" cy="9.5" r="1.4" />
      <circle cx="22.5" cy="22.5" r="1.4" />
      <circle cx="9.5" cy="22.5" r="1.4" />
      <circle cx="9.5" cy="9.5" r="1.4" />
      {/* Conectores radiales */}
      <path d="M16 12.8V8.8M16 23.2v-4M19.2 16h4M8.8 16h4" />
      <path d="m18.5 13.5 2.5-2.5m-5 5-2.5 2.5m5 0 2.5 2.5m-5-5-2.5-2.5" />
      {/* Anillo exterior de satélites */}
      <circle cx="16" cy="16" r="12" strokeDasharray="1.5 4" opacity="0.6" />
    </svg>
  )
}

// 🌻 Flor botánica detallada para Franjas Florales (3D - Mockup 0)
export function BotanicalFlowerIcon({ className = 'w-7 h-7', color = 'currentColor' }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className}>
      {/* Tallo */}
      <path d="M16 21v8" />
      <path d="M16 24c-2.5-.5-4-2-4-4 2 .5 4 2 4 4Z" />
      <path d="M16 25c2.5-.5 4-2 4-4-2 .5-4 2-4 4Z" />
      {/* Centro floral con textura */}
      <circle cx="16" cy="12" r="3.8" strokeWidth="1.8" />
      <circle cx="16" cy="12" r="1.8" strokeDasharray="1.2 1.2" />
      {/* Pétalos radiales */}
      <path d="M16 4.5v3.7M16 15.8v3.7M8.5 12h3.7M19.8 12h3.7" />
      <path d="m10.7 6.7 2.6 2.6m5.4 5.4 2.6 2.6M10.7 17.3l2.6-2.6m5.4-5.4 2.6-2.6" />
      {/* Puntas de pétalos */}
      <circle cx="16" cy="4" r="1.2" />
      <circle cx="16" cy="20" r="1.2" />
      <circle cx="8" cy="12" r="1.2" />
      <circle cx="24" cy="12" r="1.2" />
      <circle cx="10.2" cy="6.2" r="1.1" />
      <circle cx="21.8" cy="17.8" r="1.1" />
      <circle cx="10.2" cy="17.8" r="1.1" />
      <circle cx="21.8" cy="6.2" r="1.1" />
    </svg>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
   BARRA DE PROGRESO HORIZONTAL SEGMENTADA
   ────────────────────────────────────────────────────────────────────────── */
export function LandUseProgressBar({
  cropPct = 0,
  naturalPct = 0,
  floralPct = 0,
  title = 'Distribución de Superficie',
  totalLabel = '100.0% Total',
}) {
  const total = cropPct + naturalPct + floralPct
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
        <span className="tracking-tight">{title}</span>
        <span className="font-mono text-slate-400 dark:text-slate-500 font-medium">
          {totalLabel || `${total.toFixed(1)}% Total`}
        </span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-200/80 p-0.5 shadow-inner dark:bg-slate-950/80 border border-slate-300/40 dark:border-slate-800">
        <div
          style={{ width: `${Math.max(0, cropPct)}%` }}
          className="bg-emerald-500 transition-all duration-500 shadow-xs"
          title={`Cultivo: ${cropPct.toFixed(1)}%`}
        />
        <div
          style={{ width: `${Math.max(0, naturalPct)}%` }}
          className="bg-sky-400 transition-all duration-500 shadow-xs"
          title={`Seminatural: ${naturalPct.toFixed(1)}%`}
        />
        <div
          style={{ width: `${Math.max(0, floralPct)}%` }}
          className="bg-amber-400 transition-all duration-500 shadow-xs"
          title={`Franjas: ${floralPct.toFixed(1)}%`}
        />
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
   TARJETAS DE DISTRIBUCIÓN DE SUPERFICIE — VISTA 2D (Mockup 1)
   [ Ícono en cápsula de color ]  [ Nombre + % ]  [ Anillo Donut ]
   ────────────────────────────────────────────────────────────────────────── */
export function LandUse2DCards({ mix }) {
  const cropPct = Number(mix?.crop_area_pct ?? 0)
  const naturalPct = Number(mix?.natural_area_pct ?? 0)
  const floralPct = Number(mix?.floral_strips_pct ?? 0)

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
      {/* 1. Cultivo */}
      <div className="flex items-center justify-between rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3 shadow-xs transition-all hover:border-emerald-500/40 dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 shadow-xs">
            <LeafIcon className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-xs bg-[#059669] inline-block shrink-0 shadow-xs" />
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 truncate">
                Cultivo
              </span>
            </div>
            <p className="text-base sm:text-lg font-black text-slate-900 dark:text-slate-100 font-display leading-tight mt-0.5">
              {cropPct.toFixed(1)}%
            </p>
          </div>
        </div>
        <CircularProgressRing
          percentage={cropPct}
          size={46}
          strokeWidth={4.2}
          color="#10b981"
        />
      </div>

      {/* 2. Seminatural (Azul Claro) */}
      <div className="flex items-center justify-between rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3 shadow-xs transition-all hover:border-sky-500/40 dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-600 dark:text-sky-400 shadow-xs">
            <ForestMountainIcon className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-xs bg-[#38bdf8] inline-block shrink-0 shadow-xs" />
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-sky-700 dark:text-sky-300 truncate">
                Seminatural
              </span>
            </div>
            <p className="text-base sm:text-lg font-black text-slate-900 dark:text-slate-100 font-display leading-tight mt-0.5">
              {naturalPct.toFixed(1)}%
            </p>
          </div>
        </div>
        <CircularProgressRing
          percentage={naturalPct}
          size={46}
          strokeWidth={4.2}
          color="#38bdf8"
        />
      </div>

      {/* 3. Franjas Florales */}
      <div className="flex items-center justify-between rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3 shadow-xs transition-all hover:border-amber-500/40 dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 shadow-xs">
            <BouquetIcon className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-xs bg-[#f59e0b] inline-block shrink-0 shadow-xs" />
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-700 dark:text-amber-400 truncate">
                Franjas Florales
              </span>
            </div>
            <p className="text-base sm:text-lg font-black text-slate-900 dark:text-slate-100 font-display leading-tight mt-0.5">
              {floralPct.toFixed(1)}%
            </p>
          </div>
        </div>
        <CircularProgressRing
          percentage={floralPct}
          size={46}
          strokeWidth={4.2}
          color="#f59e0b"
        />
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
   TARJETAS DE DISTRIBUCIÓN DE SUPERFICIE — VISTA 3D (Mockup 0)
   [ Cuadro ícono 3D a la izquierda ]  [ Nombre en mayúsculas | % grande | Descripción ]
   ────────────────────────────────────────────────────────────────────────── */
export function LandUse3DCards({ mix }) {
  const cropPct = Number(mix?.crop_area_pct ?? 0)
  const naturalPct = Number(mix?.natural_area_pct ?? 0)
  const floralPct = Number(mix?.floral_strips_pct ?? 0)

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
      {/* 1. Cultivo */}
      <div className="flex items-center gap-3.5 rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3.5 shadow-xs transition-all hover:border-emerald-500/50 dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-600 dark:text-emerald-400 shadow-sm">
          <Wheat3DIcon className="w-7 h-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="h-2.5 w-2.5 rounded-xs bg-[#059669] inline-block shrink-0 shadow-xs" />
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 truncate">
              Cultivo
            </p>
          </div>
          <p className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 font-display leading-tight">
            {cropPct.toFixed(1)}%
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate font-medium">
            Capa verde agrícola
          </p>
        </div>
      </div>

      {/* 2. Seminatural (Azul Claro) */}
      <div className="flex items-center gap-3.5 rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3.5 shadow-xs transition-all hover:border-sky-500/50 dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-sky-500/15 border border-sky-500/40 text-sky-600 dark:text-sky-400 shadow-sm">
          <EcologyNetworkIcon className="w-7 h-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="h-2.5 w-2.5 rounded-xs bg-[#38bdf8] inline-block shrink-0 shadow-xs" />
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-sky-700 dark:text-sky-300 truncate">
              Seminatural
            </p>
          </div>
          <p className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 font-display leading-tight">
            {naturalPct.toFixed(1)}%
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate font-medium">
            Hábitat conservado
          </p>
        </div>
      </div>

      {/* 3. Franjas Florales */}
      <div className="flex items-center gap-3.5 rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3.5 shadow-xs transition-all hover:border-amber-500/50 dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-amber-500/15 border border-amber-500/40 text-amber-600 dark:text-amber-400 shadow-sm">
          <BotanicalFlowerIcon className="w-7 h-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="h-2.5 w-2.5 rounded-xs bg-[#f59e0b] inline-block shrink-0 shadow-xs" />
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-amber-700 dark:text-amber-400 truncate">
              Franjas Florales
            </p>
          </div>
          <p className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 font-display leading-tight">
            {floralPct.toFixed(1)}%
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate font-medium">
            Corredor biológico
          </p>
        </div>
      </div>
    </div>
  )
}
