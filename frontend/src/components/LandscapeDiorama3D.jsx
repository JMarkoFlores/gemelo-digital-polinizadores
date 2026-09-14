import { useRef, useMemo, useState, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'

// Pseudo-random noise function for deterministic spatial clustering
export function deterministicHash(x, z, seed = 42) {
  const n = Math.sin(x * 12.9898 + z * 78.233 + seed * 137.5) * 43758.5453
  return n - Math.floor(n)
}

/**
 * Generates a 10x10 grid (100 cells) where each cell strictly equals 1% of total area.
 * Cells are spatially clustered using distance to natural and floral focus centers,
 * producing realistic continuous patches rather than purely random noise.
 */
export function generateLandscapeGrid(mix, seed = 101) {
  const cropPct = Number(mix?.crop_area_pct ?? 70)
  const naturalPct = Number(mix?.natural_area_pct ?? 20)
  const floralPct = Number(mix?.floral_strips_pct ?? 10)

  const naturalTarget = Math.max(0, Math.min(100, Math.round(naturalPct)))
  const floralTarget = Math.max(0, Math.min(100 - naturalTarget, Math.round(floralPct)))
  const cropTarget = Math.max(0, Math.min(100 - naturalTarget - floralTarget, Math.round(cropPct)))

  // Calculate scores for each cell (x, z) from 0 to 9
  // Natural areas cluster around (0-3, 0-4) and along a border corridor
  // Floral strips buffer between natural patches and crops
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

  // Next, assign floral strips as buffer zones adjacent to natural cells or edges
  const pendingCells = cells.filter((c) => c.type === 'pending')
  pendingCells.forEach((c) => {
    // Score floral suitability based on proximity to assigned natural cells
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

  // Format cells for 3D positioning
  // Grid coordinates mapped to 3D space: x [-4.5, 4.5], z [-4.5, 4.5]
  return cells.map((cell) => {
    const worldX = (cell.x - 4.5) * 0.96
    const worldZ = (cell.z - 4.5) * 0.96

    if (cell.type === 'natural') {
      // Natural / Semi-natural vegetation: height 0.75 - 0.95
      const height = 0.72 + cell.noise * 0.24
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        color: '#065f46', // Deep forest emerald
        topColor: '#047857',
        accentColor: '#10b981',
      }
    } else if (cell.type === 'floral') {
      // Floral strips: height 0.48 - 0.58, warm amber/yellow
      const height = 0.46 + cell.noise * 0.12
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        color: '#d97706', // Warm amber
        topColor: '#f59e0b',
        accentColor: '#fbbf24',
      }
    } else if (cell.type === 'crop') {
      // Agricultural crop: height 0.30 - 0.36, low crop green
      const height = 0.30 + cell.noise * 0.08
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        color: '#15803d', // Crop green
        topColor: '#16a34a',
        accentColor: '#4ade80',
      }
    } else {
      // Empty / Unmodeled space (e.g. baseline remainder): height 0.05
      const height = 0.05 + cell.noise * 0.05
      return {
        ...cell,
        worldX,
        worldZ,
        height,
        color: '#451a03', // Dirt brown
        topColor: '#522004',
        accentColor: '#78350f',
      }
    }
  })
}

// Single Cell Mesh inside the Diorama
function LandscapeCell({ cell }) {
  const { worldX, worldZ, height, topColor, type, noise } = cell
  const halfHeight = height / 2

  return (
    <group position={[worldX, halfHeight, worldZ]}>
      {/* Extruded Cell block */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.90, height, 0.90]} />
        <meshStandardMaterial
          color={topColor}
          roughness={0.65}
          metalness={0.08}
        />
      </mesh>

      {/* Decorative details for floral strips */}
      {type === 'floral' && (
        <group position={[0, halfHeight, 0]}>
          {/* Small floral blossom clusters */}
          <mesh position={[-0.2, 0.12, -0.2]} castShadow>
            <sphereGeometry args={[0.09, 8, 8]} />
            <meshStandardMaterial color="#f43f5e" roughness={0.4} />
          </mesh>
          <mesh position={[0.18, 0.14, 0.15]} castShadow>
            <sphereGeometry args={[0.10, 8, 8]} />
            <meshStandardMaterial color="#fbbf24" roughness={0.4} />
          </mesh>
          <mesh position={[0.05, 0.10, -0.15]} castShadow>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshStandardMaterial color="#f472b6" roughness={0.4} />
          </mesh>
        </group>
      )}

      {/* Decorative foliage canopy for seminatural habitat */}
      {type === 'natural' && (
        <group position={[0, halfHeight, 0]}>
          <mesh position={[0, 0.22, 0]} castShadow>
            <coneGeometry args={[0.34, 0.52, 6]} />
            <meshStandardMaterial color="#064e3b" roughness={0.8} />
          </mesh>
          {noise > 0.45 && (
            <mesh position={[0.22, 0.18, 0.18]} castShadow>
              <coneGeometry args={[0.24, 0.40, 5]} />
              <meshStandardMaterial color="#047857" roughness={0.8} />
            </mesh>
          )}
        </group>
      )}

      {/* Small subtle furrows for crops */}
      {type === 'crop' && (
        <group position={[0, halfHeight + 0.01, 0]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[0.82, 0.82]} />
            <meshStandardMaterial color="#166534" roughness={0.9} />
          </mesh>
        </group>
      )}
    </group>
  )
}

// Diorama Pedestal Base
function DioramaPlinth() {
  return (
    <group position={[0, -0.32, 0]}>
      {/* Top soil layer */}
      <mesh position={[0, 0.14, 0]} receiveShadow>
        <boxGeometry args={[10.2, 0.24, 10.2]} />
        <meshStandardMaterial color="#451a03" roughness={0.9} />
      </mesh>
      {/* Architectural stone pedestal base */}
      <mesh position={[0, -0.16, 0]} receiveShadow>
        <boxGeometry args={[10.6, 0.36, 10.6]} />
        <meshStandardMaterial color="#1e293b" roughness={0.7} metalness={0.15} />
      </mesh>
      {/* Beveled plinth foot */}
      <mesh position={[0, -0.38, 0]} receiveShadow>
        <boxGeometry args={[11.0, 0.12, 11.0]} />
        <meshStandardMaterial color="#0f172a" roughness={0.8} />
      </mesh>
    </group>
  )
}

// Rotating World Wrapper (Optional smooth auto-rotation)
function DioramaWorld({ cells, autoRotate }) {
  const groupRef = useRef()

  useFrame((_, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.25
    }
  })

  return (
    <group ref={groupRef}>
      <DioramaPlinth />
      {cells.map((cell, idx) => (
        <LandscapeCell key={`${cell.x}-${cell.z}-${idx}`} cell={cell} />
      ))}
    </group>
  )
}

/**
 * Single 3D Scene Viewer with dedicated OrbitControls and Lighting
 */
function SingleDioramaScene({ mix, title, subtitle, optimal }) {
  const [autoRotate, setAutoRotate] = useState(false)
  const controlsRef = useRef()

  // Deterministic seed: baseline uses seed 42, optimal uses seed 84 to preserve spatial continuity
  const seed = optimal ? 84 : 42
  const cells = useMemo(() => generateLandscapeGrid(mix, seed), [mix, seed])

  const cropPct = Number(mix?.crop_area_pct ?? 0)
  const naturalPct = Number(mix?.natural_area_pct ?? 0)
  const floralPct = Number(mix?.floral_strips_pct ?? 0)
  const totalPct = cropPct + naturalPct + floralPct

  const handleResetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset()
    }
  }

  return (
    <div
      id={`diorama-card-${optimal ? 'optimal' : 'baseline'}`}
      className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/90 dark:bg-slate-900/90"
    >
      <div>
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-slate-100 font-display text-base">
              {title}
            </h3>
            {subtitle && (
              <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
            )}
          </div>
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
        </div>

        {/* 3D Canvas Diorama Container */}
        <div className="relative z-0 h-72 w-full overflow-hidden rounded-xl border border-slate-200/80 bg-gradient-to-b from-slate-100 to-slate-200/70 dark:border-slate-800 dark:from-slate-950 dark:to-slate-900">
          <Canvas
            shadows
            camera={{ position: [11.5, 10.5, 12.5], fov: 42 }}
            gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
          >
            {/* Lighting setup for crisp architectural diorama */}
            <ambientLight intensity={0.7} />
            <directionalLight
              position={[12, 18, 10]}
              intensity={1.5}
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
            <directionalLight position={[-10, 8, -10]} intensity={0.4} color="#93c5fd" />
            <hemisphereLight skyColor="#ffffff" groundColor="#334155" intensity={0.4} />

            {/* Diorama 3D Scene */}
            <DioramaWorld cells={cells} autoRotate={autoRotate} />

            {/* Independent OrbitControls */}
            <OrbitControls
              ref={controlsRef}
              enableDamping={true}
              dampingFactor={0.08}
              maxPolarAngle={Math.PI / 2.08} // Don't allow viewing underneath the plinth
              minDistance={7}
              maxDistance={26}
            />
          </Canvas>

          {/* Floating HUD controls */}
          <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 z-10">
            <button
              id={`btn-rotate-${optimal ? 'opt' : 'base'}`}
              type="button"
              onClick={() => setAutoRotate(!autoRotate)}
              title={autoRotate ? 'Detener rotación' : 'Activar giro automático'}
              className={`rounded-lg px-2 py-1 text-[11px] font-medium backdrop-blur-md transition-all shadow-xs ${
                autoRotate
                  ? 'bg-emerald-500 text-white shadow-emerald-500/20'
                  : 'bg-black/50 hover:bg-black/70 text-white/90'
              }`}
            >
              {autoRotate ? '⏸ Girando' : '▶ Girar'}
            </button>
            <button
              id={`btn-reset-${optimal ? 'opt' : 'base'}`}
              type="button"
              onClick={handleResetCamera}
              title="Restablecer ángulo de cámara"
              className="rounded-lg bg-black/50 hover:bg-black/70 px-2 py-1 text-[11px] font-medium text-white/90 backdrop-blur-md transition-all shadow-xs"
            >
              ↺ Reset
            </button>
          </div>

          <div className="pointer-events-none absolute bottom-2 left-2 rounded-md bg-black/60 px-2 py-0.5 text-[10px] text-white/90 backdrop-blur-xs font-mono">
            Grilla 10×10 (1 celda = 1% área) • 3D Interactivo
          </div>
        </div>

        {/* Proportional Land-Use Progress Bar */}
        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-xs font-medium text-slate-600 dark:text-slate-300">
            <span>Distribución de Superficie</span>
            <span className="font-mono text-slate-400">{totalPct.toFixed(1)}% Total</span>
          </div>
          <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              style={{ width: `${cropPct}%` }}
              className="bg-emerald-600 transition-all"
              title={`Cultivo: ${cropPct.toFixed(1)}%`}
            />
            <div
              style={{ width: `${naturalPct}%` }}
              className="bg-emerald-800 transition-all"
              title={`Seminatural: ${naturalPct.toFixed(1)}%`}
            />
            <div
              style={{ width: `${floralPct}%` }}
              className="bg-amber-500 transition-all"
              title={`Franjas: ${floralPct.toFixed(1)}%`}
            />
          </div>
        </div>

        {/* 3D Color & Structure Legend */}
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl border border-emerald-600/20 bg-emerald-600/[0.04] p-2.5 dark:bg-emerald-600/[0.08]">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <span className="h-3 w-3 rounded-xs bg-emerald-600 inline-block shadow-xs" />
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
                Cultivo
              </p>
            </div>
            <p className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {cropPct.toFixed(1)}%
            </p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
              Bloque bajo (0.3m)
            </p>
          </div>

          <div className="rounded-xl border border-emerald-900/20 bg-emerald-900/[0.04] p-2.5 dark:bg-emerald-900/[0.08]">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <span className="h-3 w-3 rounded-xs bg-emerald-800 inline-block shadow-xs" />
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                Seminatural
              </p>
            </div>
            <p className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {naturalPct.toFixed(1)}%
            </p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
              Bloque alto + árboles
            </p>
          </div>

          <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-2.5 dark:bg-amber-500/[0.08]">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <span className="h-3 w-3 rounded-xs bg-amber-500 inline-block shadow-xs" />
              <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                Franjas Florales
              </p>
            </div>
            <p className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {floralPct.toFixed(1)}%
            </p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
              Medio + flores 3D
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Main LandscapeDiorama3D Component
 * Renders side-by-side 3D diorama scenes for Baseline vs Optimal landscapes
 */
export default function LandscapeDiorama3D({ baselineMix, optimalMix }) {
  return (
    <div id="landscape-diorama-3d" className="space-y-4">
      <div className="grid gap-5 xl:grid-cols-2">
        <SingleDioramaScene
          title="Paisaje Base (3D)"
          subtitle="Maqueta esquemática de la configuración original"
          mix={baselineMix}
          optimal={false}
        />
        <SingleDioramaScene
          title="Paisaje Optimizado (3D)"
          subtitle="Maqueta esquemática de la solución óptima recomendada"
          mix={optimalMix}
          optimal={true}
        />
      </div>
      <p className="text-center text-xs text-slate-500 dark:text-slate-400">
        💡 <strong>Tip interactivo:</strong> Haz clic y arrastra sobre cada maqueta para orbitar/rotar en 3D. Usa la rueda del mouse o gesto de pellizco para acercar y alejar el zoom.
      </p>
    </div>
  )
}
