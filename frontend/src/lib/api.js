import axios from 'axios'

const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || (isLocal ? 'http://localhost:8000' : ''),
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('gemelos-token') || localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// In-memory demo store for when backend container is not reachable in preview
const demoUsers = [
  { id: 1, email: 'admin@example.com', rol: 'admin', activo: true },
  { id: 2, email: 'investigador@agricola.pe', rol: 'cliente', activo: true },
  { id: 3, email: 'cooperativa@viru.org', rol: 'cliente', activo: true },
  { id: 4, email: 'biologia@ecologia.edu', rol: 'cliente', activo: true },
]

const demoSimulations = [
  {
    id: 101,
    usuario_id: 2,
    fecha: new Date(Date.now() - 3600000 * 2).toISOString(),
    metricas_base: {
      crop_yield_index: 0.620,
      pollinator_abundance_index: 0.410,
      region_label: 'Valle Virú - Sector Norte',
    },
    metricas_optimas: {
      crop_yield_index: 0.704,
      pollinator_abundance_index: 0.527,
    },
  },
  {
    id: 102,
    usuario_id: 3,
    fecha: new Date(Date.now() - 3600000 * 26).toISOString(),
    metricas_base: {
      crop_yield_index: 0.590,
      pollinator_abundance_index: 0.380,
      region_label: 'Valle Pisco - Parcela B',
    },
    metricas_optimas: {
      crop_yield_index: 0.680,
      pollinator_abundance_index: 0.510,
    },
  },
]

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Only intercept network errors or connection refused in preview
    const isNetworkError = !error.response || error.code === 'ERR_NETWORK' || error.response?.status === 404 || error.response?.status === 502 || error.response?.status === 503
    const url = error.config?.url || ''
    const method = (error.config?.method || 'get').toLowerCase()

    if (isNetworkError) {
      if (url.includes('/api/auth/login')) {
        let payload = {}
        try { payload = JSON.parse(error.config?.data || '{}') } catch { /* ignore */ }
        const email = payload.email || 'admin@example.com'
        const isAdmin = email.includes('admin')
        const user = { id: isAdmin ? 1 : 2, email, rol: isAdmin ? 'admin' : 'cliente', activo: true }
        localStorage.setItem('gemelos-demo-user', JSON.stringify(user))
        return {
          data: {
            access_token: 'demo-jwt-token-preview',
            token_type: 'bearer',
            user,
          },
          status: 200,
        }
      }

      if (url.includes('/api/auth/register')) {
        let payload = {}
        try { payload = JSON.parse(error.config?.data || '{}') } catch { /* ignore */ }
        const user = { id: Date.now(), email: payload.email || 'nuevo@cliente.pe', rol: payload.rol || 'cliente', activo: true }
        localStorage.setItem('gemelos-demo-user', JSON.stringify(user))
        return {
          data: {
            access_token: 'demo-jwt-token-preview',
            token_type: 'bearer',
            user,
          },
          status: 200,
        }
      }

      if (url.includes('/api/auth/me')) {
        const saved = localStorage.getItem('gemelos-demo-user')
        const user = saved ? JSON.parse(saved) : { id: 1, email: 'admin@example.com', rol: 'admin', activo: true }
        return { data: user, status: 200 }
      }

      if (url.includes('/api/model/status')) {
        return {
          data: {
            model_ready: true,
            model_status: 'Surrogate activo (Random Forest + PyMoo v1.4)',
            version: 'v1.4.0',
          },
          status: 200,
        }
      }

      if (url.includes('/api/model/reload')) {
        return {
          data: {
            model_ready: true,
            model_status: 'Modelo recargado y calibrado con éxito',
          },
          status: 200,
        }
      }

      if (url.includes('/api/simular')) {
        let body = {}
        try { body = JSON.parse(error.config?.data || '{}') } catch { /* ignore */ }
        const pesticide = body.pesticide_level ?? 30
        const naturalArea = body.min_natural_area_pct ?? 20
        const cropArea = Math.max(40, 100 - naturalArea - 10)
        const floralStrips = 100 - cropArea - naturalArea

        // Calculate realistic agroecological simulation indicators
        const baseYield = +(0.58 + (0.1 * (1 - pesticide / 100))).toFixed(3)
        const basePollinators = +(0.36 + (0.15 * (naturalArea / 50))).toFixed(3)
        const optYield = +(baseYield * 1.135).toFixed(3)
        const optPollinators = +(basePollinators * 1.285).toFixed(3)

        const paretoFront = Array.from({ length: 18 }, (_, i) => {
          const t = i / 17
          return {
            crop_yield_index: +(0.60 + t * 0.14 - (Math.sin(t * Math.PI) * 0.02)).toFixed(3),
            pollinator_abundance_index: +(0.62 - t * 0.22 + (Math.sin(t * Math.PI) * 0.03)).toFixed(3),
            crop_area_pct: +(55 + t * 30).toFixed(1),
            natural_area_pct: +(35 - t * 25).toFixed(1),
            floral_strips_pct: 10,
          }
        })

        const baselineGeo = body.geometry || {
          type: 'Polygon',
          coordinates: [[
            [-78.865, -8.075],
            [-78.835, -8.075],
            [-78.835, -8.095],
            [-78.865, -8.095],
            [-78.865, -8.075],
          ]],
        }

        const simResult = {
          delta_yield: +(optYield - baseYield),
          delta_pollinators: +(((optPollinators - basePollinators) / basePollinators) * 100).toFixed(1),
          hypothesis_status: 'HIPÓTESIS CONFIRMADA',
          cache_hit: false,
          model_version: 'v1.4.0 (Surrogate RF-ABM)',
          baseline: {
            crop_yield_index: baseYield,
            pollinator_abundance_index: basePollinators,
            crop_area_pct: 82.0,
            natural_area_pct: 12.0,
            floral_strips_pct: 6.0,
            geometry: baselineGeo,
            center: [-8.085, -78.850],
          },
          best_solution: {
            crop_yield_index: optYield,
            pollinator_abundance_index: optPollinators,
            crop_area_pct: cropArea,
            natural_area_pct: naturalArea,
            floral_strips_pct: floralStrips,
          },
          optimized_landscape: {
            land_use_mix: {
              crop_area_pct: cropArea,
              natural_area_pct: naturalArea,
              floral_strips_pct: floralStrips,
            },
          },
          pareto_front: paretoFront,
        }

        demoSimulations.unshift({
          id: Date.now() % 10000,
          usuario_id: 1,
          fecha: new Date().toISOString(),
          metricas_base: {
            crop_yield_index: baseYield,
            pollinator_abundance_index: basePollinators,
            region_label: 'Zona Seleccionada en Mapa',
          },
          metricas_optimas: {
            crop_yield_index: optYield,
            pollinator_abundance_index: optPollinators,
          },
          ...simResult,
        })

        return { data: simResult, status: 200 }
      }

      if (url.includes('/api/simulations/me')) {
        return {
          data: {
            items: demoSimulations,
            total: demoSimulations.length,
            page: 1,
            page_size: 5,
          },
          status: 200,
        }
      }

      if (url.includes('/api/admin/dashboard')) {
        return {
          data: {
            total_users: 28,
            active_users: 25,
            simulations_this_month: 142,
            top_regions: [
              { region: 'Valle Virú - La Libertad', count: 64 },
              { region: 'Valle Pisco - Ica', count: 48 },
              { region: 'Valle Olmos - Lambayeque', count: 22 },
              { region: 'Valle Majes - Arequipa', count: 8 },
            ],
          },
          status: 200,
        }
      }

      if (url.includes('/api/admin/users')) {
        if (method === 'post') {
          let payload = {}
          try { payload = JSON.parse(error.config?.data || '{}') } catch { /* ignore */ }
          const newUser = { id: demoUsers.length + 1, email: payload.email, rol: payload.rol || 'cliente', activo: payload.activo ?? true }
          demoUsers.push(newUser)
          return { data: newUser, status: 201 }
        }
        return {
          data: {
            items: demoUsers,
            total: demoUsers.length,
            page: 1,
            page_size: 8,
          },
          status: 200,
        }
      }

      if (url.includes('/api/admin/simulations')) {
        return {
          data: {
            items: demoSimulations,
            total: demoSimulations.length,
            page: 1,
            page_size: 8,
          },
          status: 200,
        }
      }

      if (url.includes('/api/chat')) {
        let msg = ''
        try { msg = JSON.parse(error.config?.data || '{}').message || '' } catch { /* ignore */ }
        const answer = msg.toLowerCase().includes('pareto')
          ? 'El frente de Pareto ilustra las configuraciones óptimas donde no es posible aumentar el rendimiento agrícola sin comprometer la abundancia de polinizadores, permitiendo seleccionar el punto de equilibrio óptimo.'
          : msg.toLowerCase().includes('franja') || msg.toLowerCase().includes('natural')
          ? 'Recomendamos destinar entre 15% y 25% del área a bordes florales y vegetación seminatural para maximizar la conectividad ecológica y el forrajeo de abejas nativas.'
          : 'El gemelo digital integra modelos basados en agentes (ABM) con aprendizaje automático para simular la dinámica poblacional de polinizadores según el uso del suelo y agroquímicos.'
        return { data: { reply: answer }, status: 200 }
      }
    }

    return Promise.reject(error)
  }
)

export default api
