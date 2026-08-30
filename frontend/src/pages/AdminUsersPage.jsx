import { useEffect, useState } from 'react'
import api from '../lib/api'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

const emptyForm = { email: '', password: '', rol: 'cliente', activo: true }

export default function AdminUsersPage() {
  const [users, setUsers] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const loadUsers = () => {
    api
      .get(`/api/admin/users?page=${page}&page_size=8&search=${encodeURIComponent(search)}`)
      .then((response) => {
        setUsers(response.data.items)
        setTotal(response.data.total)
      })
      .catch((requestError) => setError(requestError.response?.data?.detail || 'No fue posible cargar usuarios.'))
  }

  useEffect(() => {
    loadUsers()
  }, [page])

  const createUser = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/api/admin/users', form)
      setMessage('Usuario creado correctamente.')
      setForm(emptyForm)
      loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible crear el usuario.')
    }
  }

  const toggleUser = async (user) => {
    await api.put(`/api/admin/users/${user.id}`, { activo: !user.activo })
    loadUsers()
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">Admin</p>
        <h1 className="mt-3 text-4xl font-semibold">Gestion de usuarios</h1>
      </section>
      {message ? <StatusBanner tone="success">{message}</StatusBanner> : null}
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <PanelCard title="Nuevo usuario" subtitle="Alta rapida con rol y estado inicial.">
          <form className="space-y-4" onSubmit={createUser}>
            <input value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Correo" className="w-full rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
            <input value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Contrasena" type="password" className="w-full rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
            <div className="grid gap-4 md:grid-cols-2">
              <select value={form.rol} onChange={(e) => setForm((prev) => ({ ...prev, rol: e.target.value }))} className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950">
                <option value="cliente">Cliente</option>
                <option value="admin">Admin</option>
              </select>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700">
                <input type="checkbox" checked={form.activo} onChange={(e) => setForm((prev) => ({ ...prev, activo: e.target.checked }))} />
                Activo
              </label>
            </div>
            <button className="rounded-2xl bg-primary-600 px-4 py-3 text-sm font-medium text-white">Crear usuario</button>
          </form>
        </PanelCard>
        <PanelCard
          title="Listado de usuarios"
          subtitle="Busqueda, activacion y suspension sobre endpoints reales del backend."
          actions={<button onClick={loadUsers} className="rounded-2xl bg-slate-200 px-4 py-2 text-sm dark:bg-slate-800">Refrescar</button>}
        >
          <div className="mb-4 flex gap-3">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por correo" className="flex-1 rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
            <button onClick={() => { setPage(1); loadUsers() }} className="rounded-2xl bg-primary-600 px-4 py-3 text-sm text-white">Buscar</button>
          </div>
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400">
                  <th className="pb-3">Correo</th>
                  <th className="pb-3">Rol</th>
                  <th className="pb-3">Estado</th>
                  <th className="pb-3">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t border-slate-200 dark:border-slate-800">
                    <td className="py-3">{user.email}</td>
                    <td className="py-3">{user.rol}</td>
                    <td className="py-3">{user.activo ? 'Activo' : 'Suspendido'}</td>
                    <td className="py-3">
                      <button onClick={() => toggleUser(user)} className="rounded-2xl bg-slate-200 px-3 py-2 dark:bg-slate-800">
                        {user.activo ? 'Suspender' : 'Activar'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-slate-500 dark:text-slate-400">{total} usuarios</span>
            <div className="flex gap-2">
              <button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">Anterior</button>
              <button onClick={() => setPage((value) => value + 1)} disabled={page * 8 >= total} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">Siguiente</button>
            </div>
          </div>
        </PanelCard>
      </div>
    </div>
  )
}
