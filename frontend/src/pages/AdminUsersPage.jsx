import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../lib/api'
import PanelCard from '../components/PanelCard'
import StatusBanner from '../components/StatusBanner'

const emptyForm = { email: '', password: '', rol: 'cliente', activo: true }

export default function AdminUsersPage() {
  const { t } = useTranslation()
  const [users, setUsers] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadUsers = () => {
    api
      .get(`/api/admin/users?page=${page}&page_size=8&search=${encodeURIComponent(search)}`)
      .then((response) => {
        setUsers(response.data.items)
        setTotal(response.data.total)
      })
      .catch((requestError) => setError(requestError.response?.data?.detail || t('adminUsers_errorLoad')))
  }

  useEffect(() => {
    loadUsers()
  }, [page])

  const createUser = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)
    try {
      await api.post('/api/admin/users', form)
      setMessage(t('adminUsers_created'))
      setForm(emptyForm)
      loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || t('adminUsers_errorCreate'))
    } finally {
      setSubmitting(false)
    }
  }

  const toggleUser = async (user) => {
    await api.put(`/api/admin/users/${user.id}`, { activo: !user.activo })
    loadUsers()
  }

  const totalPages = Math.max(1, Math.ceil(total / 8))

  return (
    <div className="space-y-6 sm:space-y-8">
      <section>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          {t('adminHome_badge')}
        </span>
        <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-display">
          {t('adminUsers_title')}
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Alta de usuarios, asignación de roles (cliente/administrador) y control de acceso.
        </p>
      </section>

      {message ? <StatusBanner tone="success">{message}</StatusBanner> : null}
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        {/* Create user card */}
        <PanelCard
          title={t('adminUsers_newUser_title')}
          subtitle={t('adminUsers_newUser_sub')}
        >
          <form className="space-y-4" onSubmit={createUser}>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Correo Electrónico
              </label>
              <input
                value={form.email}
                onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder={t('adminUsers_emailPlaceholder')}
                type="email"
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Contraseña Temporal
              </label>
              <input
                value={form.password}
                onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                placeholder={t('adminUsers_passwordPlaceholder')}
                type="password"
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Rol del Sistema
                </label>
                <select
                  value={form.rol}
                  onChange={(e) => setForm((prev) => ({ ...prev, rol: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm font-medium text-slate-900 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
                >
                  <option value="cliente">{t('adminUsers_roleClient')}</option>
                  <option value="admin">{t('adminUsers_roleAdmin')}</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Estado Inicial
                </label>
                <label className="flex h-[42px] cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white px-3.5 text-xs sm:text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.activo}
                    onChange={(e) => setForm((prev) => ({ ...prev, activo: e.target.checked }))}
                    className="h-4 w-4 rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>{t('adminUsers_active')}</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-emerald-600 px-4 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-xs transition hover:bg-emerald-500 disabled:opacity-50"
            >
              {submitting ? 'Creando...' : t('adminUsers_createBtn')}
            </button>
          </form>
        </PanelCard>

        {/* User list card */}
        <PanelCard
          title={t('adminUsers_list_title')}
          subtitle={t('adminUsers_list_sub')}
          actions={
            <button
              onClick={loadUsers}
              className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/>
              </svg>
              <span>{t('adminUsers_refresh')}</span>
            </button>
          }
        >
          {/* Search bar */}
          <div className="mb-4 flex gap-2">
            <div className="relative flex-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setPage(1)
                    loadUsers()
                  }
                }}
                placeholder={t('adminUsers_searchPlaceholder')}
                className="w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 py-2 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>
            <button
              onClick={() => { setPage(1); loadUsers() }}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-500"
            >
              {t('adminUsers_searchBtn')}
            </button>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-200/80 dark:border-slate-800">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200/80 dark:border-slate-800">
                <tr className="text-left font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <th className="px-4 py-3">{t('adminUsers_colEmail')}</th>
                  <th className="px-4 py-3">{t('adminUsers_colRole')}</th>
                  <th className="px-4 py-3">{t('adminUsers_colStatus')}</th>
                  <th className="px-4 py-3 text-right">{t('adminUsers_colActions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {users.map((user) => (
                  <tr key={user.id} className="transition hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-[11px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {user.email?.charAt(0).toUpperCase()}
                        </div>
                        <span>{user.email}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        user.rol === 'admin'
                          ? 'bg-purple-500/10 text-purple-700 dark:text-purple-300'
                          : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                      }`}>
                        {user.rol}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${user.activo ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                        <span className="text-slate-600 dark:text-slate-400">
                          {user.activo ? t('adminUsers_statusActive') : t('adminUsers_statusSuspended')}
                        </span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => toggleUser(user)}
                        className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                          user.activo
                            ? 'border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300'
                            : 'border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300'
                        }`}
                      >
                        {user.activo ? t('adminUsers_suspend') : t('adminUsers_activate')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between text-xs font-medium text-slate-500 dark:text-slate-400">
            <span>{t('adminUsers_total', { count: total })}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={page === 1}
                className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
              >
                {t('adminUsers_prev')}
              </button>
              <button
                onClick={() => setPage((value) => value + 1)}
                disabled={page >= totalPages}
                className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
              >
                {t('adminUsers_next')}
              </button>
            </div>
          </div>
        </PanelCard>
      </div>
    </div>
  )
}
