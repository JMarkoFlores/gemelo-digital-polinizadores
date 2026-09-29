/**
 * Paleta de colores centralizada para tipos de uso de suelo agroecológico
 * Compartida sincronizadamente entre la Vista Satelital 2D y el Diorama 3D
 */
export const LAND_USE_PALETTE = {
  crop: {
    key: 'crop',
    label: 'Cultivo',
    hex: '#059669', // Verde esmeralda intenso agrícola
    lightHex: '#10b981',
    accentHex: '#4ade80',
    rgb: '16, 185, 129',
    rgba: (alpha = 1) => `rgba(16, 185, 129, ${alpha})`,
    twBg: 'bg-emerald-500',
    twText: 'text-emerald-700 dark:text-emerald-300',
    twBorder: 'border-emerald-500/20',
    twContainerBg: 'bg-emerald-500/[0.04] dark:bg-emerald-500/[0.08]',
    badge: '🟩',
  },
  natural: {
    key: 'natural',
    label: 'Seminatural',
    hex: '#38bdf8', // Azul cielo / Celeste suave y legible (compatible con #7EC8E3)
    lightHex: '#7ec8e3',
    accentHex: '#bae6fd',
    rgb: '56, 189, 248',
    rgba: (alpha = 1) => `rgba(56, 189, 248, ${alpha})`,
    twBg: 'bg-sky-400',
    twText: 'text-sky-700 dark:text-sky-300',
    twBorder: 'border-sky-500/20',
    twContainerBg: 'bg-sky-500/[0.04] dark:bg-sky-500/[0.08]',
    badge: '🟦',
  },
  floral: {
    key: 'floral',
    label: 'Franjas Florales',
    hex: '#f59e0b', // Ámbar cálido / Naranja
    lightHex: '#fbbf24',
    accentHex: '#fde68a',
    rgb: '245, 158, 11',
    rgba: (alpha = 1) => `rgba(245, 158, 11, ${alpha})`,
    twBg: 'bg-amber-400',
    twText: 'text-amber-700 dark:text-amber-400',
    twBorder: 'border-amber-500/20',
    twContainerBg: 'bg-amber-500/[0.04] dark:bg-amber-500/[0.08]',
    badge: '🟧',
  },
}

export default LAND_USE_PALETTE
