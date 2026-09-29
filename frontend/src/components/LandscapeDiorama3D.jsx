import { useRef, useMemo, useState, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { LAND_USE_PALETTE } from '../lib/landUseColors'
import { LandUseProgressBar, LandUse3DCards } from './LandUseDistributionCards'

// Constantes de extrusión y relieve 3D para bloque geológico sólido
const TERRAIN_BASE_BOTTOM_Y = -0.85 // Base maciza profunda (elimina efecto lámina flotante)
const TERRAIN_SURFACE_OFFSET = 0.12 // Elevación mínima sobre el plano de referencia
const VERTICAL_EXAGGERATION_FACTOR = 2.0 // Exageración vertical moderada para apreciación de relieve

// Pseudo-random noise function for deterministic spatial clustering
export function deterministicHash(x, z, seed = 42) {
  const n = Math.sin(x * 12.9898 + z * 78.233 + seed * 137.5) * 43758.5453
  return n - Math.floor(n)
}

/**
 * Generates a 10x10 grid (100 cells) where each cell strictly equals 1% of total area.
 * Cells are spatially clustered using distance to natural and floral focus centers,
 * producing realistic continuous patches rather than purely random noise.
 * Incorporates real elevation data (matrix 10x10) to sculpt topography relief.
 * (Exported for full backward compatibility with ExpandableMapCard.jsx).
 */
export function generateLandscapeGrid(mix, seed = 101, elevationData = null) {
  const cropPct = Number(mix?.crop_area_pct ?? 70)
  const naturalPct = Number(mix?.natural_area_pct ?? 20)
  const floralPct = Number(mix?.floral_strips_pct ?? 10)

  const naturalTarget = Math.max(0, Math.min(100, Math.round(naturalPct)))
  const floralTarget = Math.max(0, Math.min(100 - naturalTarget, Math.round(floralPct)))
  const cropTarget = Math.max(0, Math.min(100 - naturalTarget - floralTarget, Math.round(cropPct)))

  const cells = []
  for (let x = 0; x < 10; x++) {
    for (let z = 0; z < 10; z++) {
      const distToNaturalCore = Math.hypot(x - 2, z - 2) + deterministicHash(x, z, seed) * 1.8
      const distToEcologicalCorridor = Math.abs(x - z) * 0.7 + deterministicHash(x, z, seed + 7) * 1.2
      const naturalAffinity = 10 - Math.min(distToNaturalCore, distToEcologicalCorridor * 1.6)

      cells.push({
        x,
        z,
        naturalAffinity,
        noise: deterministicHash(x, z, seed + 13),
      })
    }
  }

  // Sort by natural affinity to pick the top `naturalTarget` cells
  cells.sort((a, b) => b.naturalAffinity - a.naturalAffinity)
  for (let i = 0; i < cells.length; i++) {
    if (i < naturalTarget) {
      cells[i].type = 'natural'
    } else {
      cells[i].type = 'pending'
    }
  }

  // Assign floral strips adjacent to natural cells or edges
  const pendingCells = cells.filter((c) => c.type === 'pending')
  pendingCells.forEach((c) => {
    let minNaturalDist = 999
    for (const nc of cells) {
      if (nc.type === 'natural') {
        const d = Math.hypot(c.x - nc.x, c.z - nc.z)
        if (d < minNaturalDist) minNaturalDist = d
      }
    }
    c.floralAffinity = 10 - minNaturalDist + c.noise * 2.0
  })

  pendingCells.sort((a, b) => b.floralAffinity - a.floralAffinity)
  for (let i = 0; i < pendingCells.length; i++) {
    if (i < floralTarget) {
      pendingCells[i].type = 'floral'
    } else {
      pendingCells[i].type = 'pending_crop'
    }
  }

  const pendingCropCells = cells.filter((c) => c.type === 'pending_crop')
  for (let i = 0; i < pendingCropCells.length; i++) {
    if (i < cropTarget) {
      pendingCropCells[i].type = 'crop'
    } else {
      pendingCropCells[i].type = 'empty'
    }
  }

  // Calculate elevation relief scaling
  const hasElevation = !!(elevationData?.available && elevationData?.matrix)
  const rangeM = Number(elevationData?.elevation_range_m ?? 0)
  const minElevM = Number(elevationData?.min_elevation_m ?? 0)

  // Format cells for 3D positioning
  return cells.map((cell) => {
    const worldX = (cell.x - 4.5) * 0.96
    const worldZ = (cell.z - 4.5) * 0.96

    let elevationM = null
    let relElevationM = null
    let terrainRelief = 0.0

    if (hasElevation) {
      const z = Math.min(9, Math.max(0, cell.z))
      const x = Math.min(9, Math.max(0, cell.x))
      elevationM = Number(elevationData.matrix[z]?.[x] ?? 0)
      const norm = Number(elevationData.normalized_matrix?.[z]?.[x] ?? 0)
      relElevationM = elevationM - minElevM

      const maxRelief = calculateReliefRange(elevationData)
      terrainRelief = norm * maxRelief
    }

    if (cell.type === 'natural') {
      const height = 0.72 + cell.noise * 0.24
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        terrainRelief,
        elevationM,
        relElevationM,
        typeLabel: 'Seminatural',
        color: '#0284c7', // sky-600
        topColor: LAND_USE_PALETTE.natural.hex, // '#38bdf8' (celeste claro)
        accentColor: LAND_USE_PALETTE.natural.accentHex, // '#bae6fd'
      }
    } else if (cell.type === 'floral') {
      const height = 0.46 + cell.noise * 0.12
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        terrainRelief,
        elevationM,
        relElevationM,
        typeLabel: 'Franja Floral',
        color: '#d97706',
        topColor: '#f59e0b',
        accentColor: '#fbbf24',
      }
    } else if (cell.type === 'crop') {
      const height = 0.30 + cell.noise * 0.08
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        terrainRelief,
        elevationM,
        relElevationM,
        typeLabel: 'Cultivo',
        color: '#15803d',
        topColor: '#16a34a',
        accentColor: '#4ade80',
      }
    } else {
      const height = 0.05 + cell.noise * 0.05
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        terrainRelief,
        elevationM,
        relElevationM,
        typeLabel: 'Sin modelar',
        color: '#451a03',
        topColor: '#522004',
        accentColor: '#78350f',
      }
    }
  })
}

/**
 * Extracts bounding box [minLon, minLat, maxLon, maxLat] from polygon geometry
 */
export function getBBoxFromGeometry(geometry) {
  const coords = geometry?.coordinates?.[0] || []
  if (!coords.length) {
    // Default fallback: Valle de Virú (Trujillo, Perú)
    return { minLon: -78.88, minLat: -8.12, maxLon: -78.82, maxLat: -8.07 }
  }
  let minLon = 999, minLat = 999, maxLon = -999, maxLat = -999
  coords.forEach(([lon, lat]) => {
    if (lon < minLon) minLon = lon
    if (lon > maxLon) maxLon = lon
    if (lat < minLat) minLat = lat
    if (lat > maxLat) maxLat = lat
  })
  return { minLon, minLat, maxLon, maxLat }
}

/**
 * Calcula el factor de escala vertical moderado (1.8x - 2.5x) para relieve fidedigno
 * - Para desniveles mínimos (< 4m): relieve plano uniforme (0.02)
 * - Para desniveles agrícolas o serranías: curvatura visible pero balanceada
 * - Se aplica idénticamente al Paisaje Base y al Optimizado para preservar comparabilidad
 */
function calculateReliefRange(elevationData) {
  if (!elevationData?.available || !elevationData?.matrix) return 0.02
  const rangeM = Number(elevationData?.elevation_range_m ?? 0)
  if (rangeM < 4.0) return 0.02 // Terreno llano real: bloque plano sin inventar relieve
  const normalized = Math.pow(rangeM / 140.0, 0.70) * 1.80
  return Math.min(2.85, Math.max(0.42, normalized))
}

/**
 * Muestreo bilineal con interpolación Hermite Smoothstep (C1 continuo)
 * Elimina aristas angulares, picos quebrados y pliegues artificiales,
 * produciendo pendientes y colinas topográficas orgánicas y fluidas.
 */
function sampleSmoothBilinear(matrix, u, v) {
  if (!matrix || !matrix.length) return 0
  const rows = matrix.length
  const cols = matrix[0].length
  const x = Math.max(0, Math.min(cols - 1, u * (cols - 1)))
  const z = Math.max(0, Math.min(rows - 1, v * (rows - 1)))
  const x0 = Math.floor(x)
  const x1 = Math.min(cols - 1, x0 + 1)
  const z0 = Math.floor(z)
  const z1 = Math.min(rows - 1, z0 + 1)
  const fx = x - x0
  const fz = z - z0

  // Hermite smoothstep curve: 3t^2 - 2t^3 (derivada suave en fronteras de celda)
  const sx = fx * fx * (3 - 2 * fx)
  const sz = fz * fz * (3 - 2 * fz)

  const v00 = Number(matrix[z0]?.[x0] ?? 0)
  const v10 = Number(matrix[z0]?.[x1] ?? 0)
  const v01 = Number(matrix[z1]?.[x0] ?? 0)
  const v11 = Number(matrix[z1]?.[x1] ?? 0)
  return (
    (1 - sx) * (1 - sz) * v00 +
    sx * (1 - sz) * v10 +
    (1 - sx) * sz * v01 +
    sx * sz * v11
  )
}

/**
 * Shared memory cache for satellite image elements
 */
const satelliteImageCache = new Map()

/**
 * Hook to fetch and cache Esri ArcGIS World_Imagery export image for the polygon bbox
 */
function useSatelliteImage(bbox) {
  const [image, setImage] = useState(() => {
    if (!bbox) return null
    const key = `${bbox.minLon.toFixed(4)},${bbox.minLat.toFixed(4)},${bbox.maxLon.toFixed(4)},${bbox.maxLat.toFixed(4)}`
    return satelliteImageCache.get(key) || null
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!bbox) return
    const key = `${bbox.minLon.toFixed(4)},${bbox.minLat.toFixed(4)},${bbox.maxLon.toFixed(4)},${bbox.maxLat.toFixed(4)}`

    if (satelliteImageCache.has(key)) {
      setImage(satelliteImageCache.get(key))
      return
    }

    setLoading(true)
    const lonSpan = Math.abs(bbox.maxLon - bbox.minLon)
    const latSpan = Math.abs(bbox.maxLat - bbox.minLat)
    const padLon = lonSpan * 0.04
    const padLat = latSpan * 0.04
    const minX = (bbox.minLon - padLon).toFixed(6)
    const minY = (bbox.minLat - padLat).toFixed(6)
    const maxX = (bbox.maxLon + padLon).toFixed(6)
    const maxY = (bbox.maxLat + padLat).toFixed(6)

    // Esri World_Imagery Export REST API (matching the 2D Leaflet satellite tiles)
    const url = `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=${minX},${minY},${maxX},${maxY}&bboxSR=4326&imageSR=4326&size=1024,1024&format=jpg&f=image`

    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      satelliteImageCache.set(key, img)
      setImage(img)
      setLoading(false)
    }
    img.onerror = (e) => {
      console.warn('Fidelidad satelital: usando textura de terreno realista de respaldo', e)
      setLoading(false)
    }
    img.src = url
  }, [bbox?.minLon, bbox?.minLat, bbox?.maxLon, bbox?.maxLat])

  return { image, loading }
}

/**
 * Creates a dynamic CanvasTexture combining real satellite imagery
 * with subtle semi-transparent land-use overlay and cell boundary lines
 */
function createCompositeTexture(satelliteImage, cells, overlayOpacity = 0.35, hoveredCell = null) {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 1024
  const ctx = canvas.getContext('2d')

  if (satelliteImage && satelliteImage.complete && satelliteImage.naturalWidth > 0) {
    // Draw real high-resolution satellite imagery
    ctx.drawImage(satelliteImage, 0, 0, 1024, 1024)
  } else {
    // Realistic photographic aerial ground fallback (earthy vegetation/crops gradient)
    const grad = ctx.createLinearGradient(0, 0, 1024, 1024)
    grad.addColorStop(0, '#475338')
    grad.addColorStop(0.35, '#566042')
    grad.addColorStop(0.7, '#4d573d')
    grad.addColorStop(1, '#5e5a40')
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, 1024, 1024)

    // Subtle agricultural parcel patterns
    for (let i = 0; i < 24; i++) {
      ctx.fillStyle = i % 2 === 0 ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.05)'
      ctx.fillRect((i * 128) % 1024, (i * 211) % 1024, 102, 64)
    }
  }

  const cellW = 1024 / 10
  const cellH = 1024 / 10

  // Superimpose subtle semi-transparent land-use tint
  cells.forEach((cell) => {
    const px = cell.x * cellW
    const py = cell.z * cellH

    let fillColor = null
    if (cell.type === 'crop') {
      fillColor = `rgba(${LAND_USE_PALETTE.crop.rgb}, ${0.46 * overlayOpacity})` // Verde esmeralda agrícola
    } else if (cell.type === 'natural') {
      fillColor = `rgba(${LAND_USE_PALETTE.natural.rgb}, ${0.76 * overlayOpacity})` // Celeste cielo vibrante y definido
    } else if (cell.type === 'floral') {
      fillColor = `rgba(${LAND_USE_PALETTE.floral.rgb}, ${0.54 * overlayOpacity})` // Ámbar cálido
    }

    if (fillColor && overlayOpacity > 0.02) {
      ctx.fillStyle = fillColor
      ctx.fillRect(px, py, cellW, cellH)
    }

    // Grid border line con realce celeste para parcelas Seminatural
    const isHovered = hoveredCell && hoveredCell.x === cell.x && hoveredCell.z === cell.z
    if (isHovered) {
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 3.5
      ctx.strokeRect(px + 1.5, py + 1.5, cellW - 3, cellH - 3)
      ctx.fillStyle = 'rgba(255, 255, 255, 0.22)'
      ctx.fillRect(px, py, cellW, cellH)
    } else if (cell.type === 'natural' && overlayOpacity > 0.12) {
      // Contorno celeste sutil que hace inconfundible el límite del hábitat seminatural
      ctx.strokeStyle = 'rgba(125, 211, 252, 0.70)'
      ctx.lineWidth = 1.6
      ctx.strokeRect(px + 0.8, py + 0.8, cellW - 1.6, cellH - 1.6)
    } else if (overlayOpacity > 0.05) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.20)'
      ctx.lineWidth = 1.1
      ctx.strokeRect(px + 0.6, py + 0.6, cellW - 1.2, cellH - 1.2)
    }
  })

  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = THREE.ClampToEdgeWrapping
  texture.wrapT = THREE.ClampToEdgeWrapping
  texture.generateMipmaps = true
  texture.minFilter = THREE.LinearMipmapLinearFilter
  texture.magFilter = THREE.LinearFilter
  texture.colorSpace = THREE.SRGBColorSpace
  texture.needsUpdate = true
  return texture
}

/**
 * Genera la superficie continua superior del terreno con relieve real de Open-Elevation
 * Muestreado con resolución densa (36x36) y curvatura Hermite suave sin quiebres poliédricos.
 */
function createTopTerrainGeometry(elevationData, segX = 36, segZ = 36, width = 9.6, depth = 9.6) {
  const geo = new THREE.BufferGeometry()
  const positions = []
  const uvs = []
  const indices = []

  const hasElevation = !!(elevationData?.available && elevationData?.matrix)
  const maxRelief = calculateReliefRange(elevationData)

  const countX = segX + 1
  const countZ = segZ + 1

  for (let iz = 0; iz < countZ; iz++) {
    const v = iz / segZ
    const z = (v - 0.5) * depth
    for (let ix = 0; ix < countX; ix++) {
      const u = ix / segX
      const x = (u - 0.5) * width

      let height = TERRAIN_SURFACE_OFFSET
      if (hasElevation) {
        const norm = sampleSmoothBilinear(elevationData.normalized_matrix, u, v)
        height = norm * maxRelief + TERRAIN_SURFACE_OFFSET
      }

      positions.push(x, height, z)
      uvs.push(u, 1 - v)
    }
  }

  for (let iz = 0; iz < segZ; iz++) {
    for (let ix = 0; ix < segX; ix++) {
      const a = iz * countX + ix
      const b = iz * countX + (ix + 1)
      const c = (iz + 1) * countX + ix
      const d = (iz + 1) * countX + (ix + 1)

      indices.push(a, c, b)
      indices.push(b, c, d)
    }
  }

  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  geo.setIndex(indices)
  geo.computeVertexNormals()
  return geo
}

/**
 * Genera paredes laterales extruidas hacia abajo hasta bottomY formando un bloque macizo
 * de corte geológico sólido (tipo prisma o mesa de diorama), sellando la base inferior.
 * Con orientación estricta de normales exteriores para iluminación volumétrica realista.
 */
function createTerrainSkirtGeometry(
  elevationData,
  segX = 36,
  segZ = 36,
  width = 9.6,
  depth = 9.6,
  bottomY = TERRAIN_BASE_BOTTOM_Y
) {
  const geo = new THREE.BufferGeometry()
  const positions = []
  const indices = []

  const hasElevation = !!(elevationData?.available && elevationData?.matrix)
  const maxRelief = calculateReliefRange(elevationData)

  const getHeight = (u, v) => {
    if (!hasElevation) return TERRAIN_SURFACE_OFFSET
    const norm = sampleSmoothBilinear(elevationData.normalized_matrix, u, v)
    return norm * maxRelief + TERRAIN_SURFACE_OFFSET
  }

  let idxOffset = 0
  const addWallQuad = (p0, p1, p2, p3, isReversed = false) => {
    positions.push(...p0, ...p1, ...p2, ...p3)
    if (!isReversed) {
      // Normal exterior estándar
      indices.push(idxOffset, idxOffset + 1, idxOffset + 2)
      indices.push(idxOffset, idxOffset + 2, idxOffset + 3)
    } else {
      // Normal exterior inversa
      indices.push(idxOffset, idxOffset + 2, idxOffset + 1)
      indices.push(idxOffset, idxOffset + 3, idxOffset + 2)
    }
    idxOffset += 4
  }

  // 1. Pared Norte (v = 0, z = -depth/2, normal exterior hacia -Z)
  for (let ix = 0; ix < segX; ix++) {
    const u0 = ix / segX
    const u1 = (ix + 1) / segX
    const x0 = (u0 - 0.5) * width
    const x1 = (u1 - 0.5) * width
    const z = -depth / 2
    const h0 = getHeight(u0, 0)
    const h1 = getHeight(u1, 0)
    addWallQuad([x0, h0, z], [x1, h1, z], [x1, bottomY, z], [x0, bottomY, z], false)
  }

  // 2. Pared Sur (v = 1, z = depth/2, normal exterior hacia +Z)
  for (let ix = 0; ix < segX; ix++) {
    const u0 = ix / segX
    const u1 = (ix + 1) / segX
    const x0 = (u0 - 0.5) * width
    const x1 = (u1 - 0.5) * width
    const z = depth / 2
    const h0 = getHeight(u0, 1)
    const h1 = getHeight(u1, 1)
    addWallQuad([x0, h0, z], [x1, h1, z], [x1, bottomY, z], [x0, bottomY, z], true)
  }

  // 3. Pared Oeste (u = 0, x = -width/2, normal exterior hacia -X)
  for (let iz = 0; iz < segZ; iz++) {
    const v0 = iz / segZ
    const v1 = (iz + 1) / segZ
    const z0 = (v0 - 0.5) * depth
    const z1 = (v1 - 0.5) * depth
    const x = -width / 2
    const h0 = getHeight(0, v0)
    const h1 = getHeight(0, v1)
    addWallQuad([x, h0, z0], [x, h1, z1], [x, bottomY, z1], [x, bottomY, z0], true)
  }

  // 4. Pared Este (u = 1, x = width/2, normal exterior hacia +X)
  for (let iz = 0; iz < segZ; iz++) {
    const v0 = iz / segZ
    const v1 = (iz + 1) / segZ
    const z0 = (v0 - 0.5) * depth
    const z1 = (v1 - 0.5) * depth
    const x = width / 2
    const h0 = getHeight(1, v0)
    const h1 = getHeight(1, v1)
    addWallQuad([x, h0, z0], [x, h1, z1], [x, bottomY, z1], [x, bottomY, z0], false)
  }

  // 5. Placa inferior maciza (sella la base horizontal del prisma en bottomY)
  const hw = width / 2
  const hd = depth / 2
  positions.push(-hw, bottomY, -hd, hw, bottomY, -hd, hw, bottomY, hd, -hw, bottomY, hd)
  indices.push(idxOffset, idxOffset + 2, idxOffset + 1)
  indices.push(idxOffset, idxOffset + 3, idxOffset + 2)

  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geo.setIndex(indices)
  geo.computeVertexNormals()
  return geo
}

// Pedestal arquitectónico integrado debajo de la base del prisma de terreno
function DioramaPlinth({ bottomY = TERRAIN_BASE_BOTTOM_Y }) {
  return (
    <group position={[0, bottomY, 0]}>
      {/* Estrato de corte basal oscuro */}
      <mesh position={[0, -0.06, 0]} receiveShadow>
        <boxGeometry args={[9.8, 0.12, 9.8]} />
        <meshStandardMaterial color="#1e2430" roughness={0.92} metalness={0.06} />
      </mesh>
      {/* Marco de pedestal arquitectónico biselado */}
      <mesh position={[0, -0.18, 0]} receiveShadow>
        <boxGeometry args={[10.3, 0.14, 10.3]} />
        <meshStandardMaterial color="#0f172a" roughness={0.82} metalness={0.12} />
      </mesh>
      {/* Zócalo inferior con sombra de contacto */}
      <mesh position={[0, -0.28, 0]} receiveShadow>
        <boxGeometry args={[10.7, 0.08, 10.7]} />
        <meshStandardMaterial color="#020617" roughness={0.90} />
      </mesh>
    </group>
  )
}

// Realistic Watertight 3D Terrain Diorama Mesh
function RealisticTerrainDiorama({
  satelliteImage,
  cells,
  elevationData,
  overlayOpacity,
  hoveredCell,
  onPointerMoveCell,
  onPointerOutCell,
}) {
  // Generate top textured surface geometry
  const topGeo = useMemo(
    () => createTopTerrainGeometry(elevationData, 36, 36, 9.6, 9.6),
    [elevationData]
  )

  // Generate skirt geometry (4 walls + bottom) down to solid base
  const skirtGeo = useMemo(
    () => createTerrainSkirtGeometry(elevationData, 36, 36, 9.6, 9.6, TERRAIN_BASE_BOTTOM_Y),
    [elevationData]
  )

  // Generate composite texture combining real satellite + subtle land-use overlay
  const compositeTexture = useMemo(
    () => createCompositeTexture(satelliteImage, cells, overlayOpacity, hoveredCell),
    [satelliteImage, cells, overlayOpacity, hoveredCell]
  )

  useEffect(() => {
    return () => {
      topGeo.dispose()
      skirtGeo.dispose()
      compositeTexture.dispose()
    }
  }, [topGeo, skirtGeo, compositeTexture])

  const handlePointerMove = (e) => {
    e.stopPropagation()
    const point = e.point
    const u = Math.max(0, Math.min(0.999, (point.x + 4.8) / 9.6))
    const v = Math.max(0, Math.min(0.999, (point.z + 4.8) / 9.6))
    const cellX = Math.floor(u * 10)
    const cellZ = Math.floor(v * 10)
    onPointerMoveCell({ x: cellX, z: cellZ })
  }

  return (
    <group>
      {/* Real Textured Terrain Top Surface */}
      <mesh
        geometry={topGeo}
        castShadow
        receiveShadow
        onPointerMove={handlePointerMove}
        onPointerOut={onPointerOutCell}
      >
        <meshStandardMaterial
          map={compositeTexture}
          roughness={0.80}
          metalness={0.04}
        />
      </mesh>

      {/* Side Skirts (Geological cut / Dark architectural stratum) */}
      <mesh geometry={skirtGeo} receiveShadow castShadow>
        <meshStandardMaterial
          color="#1e2430"
          roughness={0.92}
          metalness={0.06}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Pedestal */}
      <DioramaPlinth bottomY={TERRAIN_BASE_BOTTOM_Y} />
    </group>
  )
}

// Rotating World Wrapper
function DioramaWorld({
  autoRotate,
  satelliteImage,
  cells,
  elevationData,
  overlayOpacity,
  hoveredCell,
  onPointerMoveCell,
  onPointerOutCell,
}) {
  const groupRef = useRef()

  useFrame((_, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.22
    }
  })

  return (
    <group ref={groupRef}>
      <RealisticTerrainDiorama
        satelliteImage={satelliteImage}
        cells={cells}
        elevationData={elevationData}
        overlayOpacity={overlayOpacity}
        hoveredCell={hoveredCell}
        onPointerMoveCell={onPointerMoveCell}
        onPointerOutCell={onPointerOutCell}
      />
    </group>
  )
}

/**
 * Single 3D Scene Viewer with dedicated OrbitControls, Lighting, HUD and Topography badge
 */
function SingleDioramaScene({
  mix,
  title,
  subtitle,
  optimal,
  elevationData,
  geometry,
  satelliteImage,
  isImageLoading,
}) {
  const [autoRotate, setAutoRotate] = useState(false)
  const [overlayOpacity, setOverlayOpacity] = useState(0.55) // Default 55% balanced overlay for high clarity
  const [hoveredCell, setHoveredCell] = useState(null)
  const controlsRef = useRef()

  // Deterministic seed: baseline uses 42, optimal uses 84 to preserve spatial continuity
  const seed = optimal ? 84 : 42
  const cells = useMemo(
    () => generateLandscapeGrid(mix, seed, elevationData),
    [mix, seed, elevationData]
  )

  const cropPct = Number(mix?.crop_area_pct ?? 0)
  const naturalPct = Number(mix?.natural_area_pct ?? 0)
  const floralPct = Number(mix?.floral_strips_pct ?? 0)
  const totalPct = cropPct + naturalPct + floralPct

  const handleResetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset()
    }
  }

  const hasElevation = !!(elevationData?.available && elevationData?.elevation_range_m !== undefined)
  const rangeM = Number(elevationData?.elevation_range_m ?? 0)

  // Find hovered cell information for HUD pill
  const hoveredCellInfo = useMemo(() => {
    if (!hoveredCell) return null
    return cells.find((c) => c.x === hoveredCell.x && c.z === hoveredCell.z) || null
  }, [hoveredCell, cells])

  return (
    <div
      id={`diorama-card-${optimal ? 'optimal' : 'baseline'}`}
      className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/90 dark:bg-slate-900/90 transition-all"
    >
      <div>
        {/* Header */}
        <div className="mb-3 flex items-center justify-between gap-2 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 dark:text-slate-100 font-display text-base">
                {title}
              </h3>
              {satelliteImage ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                  🛰️ Satélite Esri
                </span>
              ) : isImageLoading ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2 py-0.5 text-[11px] font-semibold text-sky-700 dark:text-sky-300 animate-pulse">
                  🛰️ Cargando satélite…
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
                  🎨 Terreno fotorrealista
                </span>
              )}
            </div>
            {subtitle && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>
            )}
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            {optimal ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Recomendación IA
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                Estado Actual
              </span>
            )}

            {hasElevation ? (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2.5 py-1 text-xs font-semibold text-sky-700 dark:text-sky-300"
                title={`Desnivel real del terreno: ${rangeM.toFixed(0)} m`}
              >
                🏔️ {rangeM > 4 ? `Relieve Real (Δ ${rangeM.toFixed(0)}m)` : 'Terreno Llano'}
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-xs text-slate-400">
                🏔️ Vista plana
              </span>
            )}
          </div>
        </div>

        {/* 3D Canvas Diorama Container */}
        <div className="relative z-0 h-80 w-full overflow-hidden rounded-xl border border-slate-200/80 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 shadow-inner">
          <Canvas
            shadows
            camera={{ position: [11.5, 9.8, 12.0], fov: 42 }}
            gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
          >
            {/* Natural sunlight lighting calibrated for realistic satellite terrain relief */}
            <ambientLight intensity={0.52} />
            <directionalLight
              position={[10, 16, 9]}
              intensity={1.75}
              color="#fffbf0"
              castShadow
              shadow-mapSize-width={1024}
              shadow-mapSize-height={1024}
              shadow-camera-near={0.5}
              shadow-camera-far={40}
              shadow-camera-left={-8}
              shadow-camera-right={8}
              shadow-camera-top={8}
              shadow-camera-bottom={-8}
            />
            <directionalLight position={[-10, 9, -8]} intensity={0.42} color="#bae6fd" />
            <hemisphereLight skyColor="#ffffff" groundColor="#0f172a" intensity={0.40} />

            {/* Realistic Diorama Scene with Satellite Texture and Topographical Elevation */}
            <DioramaWorld
              autoRotate={autoRotate}
              satelliteImage={satelliteImage}
              cells={cells}
              elevationData={elevationData}
              overlayOpacity={overlayOpacity}
              hoveredCell={hoveredCell}
              onPointerMoveCell={setHoveredCell}
              onPointerOutCell={() => setHoveredCell(null)}
            />

            {/* Independent OrbitControls */}
            <OrbitControls
              ref={controlsRef}
              enableDamping={true}
              dampingFactor={0.08}
              maxPolarAngle={Math.PI / 2.05}
              minDistance={7}
              maxDistance={26}
            />
          </Canvas>

          {/* Floating Top HUD: Controls for Opacity, Auto-Rotate & Reset */}
          <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 z-10">
            {/* Overlay Opacity Selector */}
            <div className="flex items-center rounded-lg bg-black/60 p-0.5 backdrop-blur-md border border-white/10 text-[10px]">
              <button
                type="button"
                onClick={() => setOverlayOpacity(0.0)}
                className={`px-1.5 py-0.5 rounded transition ${
                  overlayOpacity === 0 ? 'bg-emerald-500 font-bold text-white' : 'text-slate-300 hover:text-white'
                }`}
                title="Mostrar únicamente la textura satelital real sin capa de uso"
              >
                Satélite
              </button>
              <button
                type="button"
                onClick={() => setOverlayOpacity(0.55)}
                className={`px-1.5 py-0.5 rounded transition ${
                  overlayOpacity === 0.55 ? 'bg-emerald-500 font-bold text-white' : 'text-slate-300 hover:text-white'
                }`}
                title="Capa de uso balanceada con visibilidad óptima de hábitat y cultivo"
              >
                Sutil (55%)
              </button>
              <button
                type="button"
                onClick={() => setOverlayOpacity(0.80)}
                className={`px-1.5 py-0.5 rounded transition ${
                  overlayOpacity === 0.80 ? 'bg-emerald-500 font-bold text-white' : 'text-slate-300 hover:text-white'
                }`}
                title="Capa de uso destacada con máximo contraste"
              >
                80%
              </button>
            </div>

            <button
              id={`btn-rotate-${optimal ? 'opt' : 'base'}`}
              type="button"
              onClick={() => setAutoRotate(!autoRotate)}
              title={autoRotate ? 'Detener rotación' : 'Activar giro automático'}
              className={`rounded-lg px-2 py-1 text-[11px] font-medium backdrop-blur-md transition-all shadow-xs border border-white/10 ${
                autoRotate
                  ? 'bg-emerald-500 text-white shadow-emerald-500/20'
                  : 'bg-black/60 hover:bg-black/80 text-white/90'
              }`}
            >
              {autoRotate ? '⏸ Girando' : '▶ Girar'}
            </button>
            <button
              id={`btn-reset-${optimal ? 'opt' : 'base'}`}
              type="button"
              onClick={handleResetCamera}
              title="Restablecer ángulo de cámara"
              className="rounded-lg bg-black/60 hover:bg-black/80 border border-white/10 px-2 py-1 text-[11px] font-medium text-white/90 backdrop-blur-md transition-all shadow-xs"
            >
              ↺ Reset
            </button>
          </div>

          {/* Floating Bottom Left HUD: Cell Inspector or Terrain Information */}
          <div className="pointer-events-none absolute bottom-2 left-2 right-2 sm:right-auto flex flex-col gap-1 z-10">
            {hoveredCellInfo ? (
              <div className="rounded-lg bg-slate-900/90 border border-emerald-500/40 px-3 py-1.5 text-xs text-white backdrop-blur-md shadow-lg flex items-center gap-2">
                <span className="font-bold text-emerald-400">
                  📍 Parcela [{hoveredCellInfo.x}, {hoveredCellInfo.z}]
                </span>
                <span className="text-slate-300">•</span>
                <span className="font-semibold text-slate-200">
                  {hoveredCellInfo.typeLabel}
                </span>
                {hoveredCellInfo.elevationM !== null && (
                  <>
                    <span className="text-slate-400">•</span>
                    <span className="text-sky-300 font-mono text-[11px]">
                      🏔️ Cota: <strong>{hoveredCellInfo.elevationM.toFixed(0)}m</strong>
                      {hoveredCellInfo.relElevationM !== null &&
                        ` (${hoveredCellInfo.relElevationM >= 0 ? '+' : ''}${hoveredCellInfo.relElevationM.toFixed(0)}m)`}
                    </span>
                  </>
                )}
              </div>
            ) : (
              <div className="rounded-md bg-black/70 border border-white/10 px-2.5 py-1 text-[10px] text-white/90 backdrop-blur-xs font-mono flex items-center gap-1.5">
                <span>🛰️ Textura satelital real + Grilla 10×10</span>
                {hasElevation ? (
                  <span className="text-sky-300">
                    • Cota: {elevationData.min_elevation_m.toFixed(0)}m–{elevationData.max_elevation_m.toFixed(0)}m (Δ {rangeM.toFixed(0)}m)
                  </span>
                ) : (
                  <span className="text-slate-400">• Terreno plano</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Proportional Land-Use Progress Bar & Redesigned 3D Cards (Mockup 0) */}
        <div className="mt-4 space-y-3">
          <LandUseProgressBar
            cropPct={cropPct}
            naturalPct={naturalPct}
            floralPct={floralPct}
            title="Distribución de Superficie"
            totalLabel={`${totalPct.toFixed(1)}% Total`}
          />
          <LandUse3DCards mix={mix} />
        </div>
      </div>
    </div>
  )
}

/**
 * Main LandscapeDiorama3D Component
 * Renders side-by-side 3D diorama scenes for Baseline vs Optimal landscapes with shared real terrain topography
 * and real satellite texture mapping.
 */
export default function LandscapeDiorama3D({
  baselineMix,
  optimalMix,
  elevationData = null,
  geometry = null,
}) {
  const bbox = useMemo(() => getBBoxFromGeometry(geometry), [geometry])
  const { image: satelliteImage, loading: isImageLoading } = useSatelliteImage(bbox)

  return (
    <div id="landscape-diorama-3d" className="space-y-4">
      {elevationData && (
        <div className="flex items-center justify-between px-1 text-xs text-slate-500 dark:text-slate-400 flex-wrap gap-2">
          <span>
            {elevationData.available
              ? `🏔️ Relieve real activo: ${elevationData.source} (Desnivel observado: ${elevationData.elevation_range_m} m)`
              : `🏔️ ${elevationData.message || 'Relieve no disponible para esta zona, mostrando vista plana.'}`}
          </span>
          <span className="text-[11px] text-slate-400 font-mono">
            Misma textura satelital y relieve topográfico en ambos dioramas (solo varía el uso de suelo)
          </span>
        </div>
      )}
      <div className="grid gap-5 xl:grid-cols-2">
        <SingleDioramaScene
          title="Paisaje Base (3D)"
          subtitle="Topografía real con textura satelital y uso de suelo actual"
          mix={baselineMix}
          optimal={false}
          elevationData={elevationData}
          geometry={geometry}
          satelliteImage={satelliteImage}
          isImageLoading={isImageLoading}
        />
        <SingleDioramaScene
          title="Paisaje Optimizado (3D)"
          subtitle="Misma topografía real con recomendación multiobjetivo"
          mix={optimalMix}
          optimal={true}
          elevationData={elevationData}
          geometry={geometry}
          satelliteImage={satelliteImage}
          isImageLoading={isImageLoading}
        />
      </div>
      <p className="text-center text-xs text-slate-500 dark:text-slate-400">
        💡 <strong>Tip interactivo:</strong> Haz clic y arrastra sobre cada maqueta para orbitar/rotar en 3D. Pasa el cursor sobre el terreno para inspeccionar parcelas individuales con su cota real en metros.
      </p>
    </div>
  )
}
