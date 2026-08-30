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
    try {
      await api.post('/api/admin/users', form)
      setMessage(t('adminUsers_created'))
      setForm(emptyForm)
      loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || t('adminUsers_errorCreate'))
    }
  }

  const toggleUser = async (user) => {
    await api.put(`/api/admin/users/${user.id}`, { activo: !user.activo })
    loadUsers()
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm uppercase tracking-[0.3em] text-primary-600">{t('adminHome_badge')}</p>
        <h1 className="mt-3 text-4xl font-semibold">{t('adminUsers_title')}</h1>
      </section>
      {message ? <StatusBanner tone="success">{message}</StatusBanner> : null}
      {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <PanelCard title={t('adminUsers_newUser_title')} subtitle={t('adminUsers_newUser_sub')}>
          <form className="space-y-4" onSubmit={createUser}>
            <input value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} placeholder={t('adminUsers_emailPlaceholder')} className="w-full rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
            <input value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} placeholder={t('adminUsers_passwordPlaceholder')} type="password" className="w-full rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
            <div className="grid gap-4 md:grid-cols-2">
              <select value={form.rol} onChange={(e) => setForm((prev) => ({ ...prev, rol: e.target.value }))} className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950">
                <option value="cliente">{t('adminUsers_roleClient')}</option>
                <option value="admin">{t('adminUsers_roleAdmin')}</option>
              </select>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700">
                <input type="checkbox" checked={form.activo} onChange={(e) => setForm((prev) => ({ ...prev, activo: e.target.checked }))} />
                {t('adminUsers_active')}
              </label>
            </div>
            <button className="rounded-2xl bg-primary-600 px-4 py-3 text-sm font-medium text-white">{t('adminUsers_createBtn')}</button>
          </form>
        </PanelCard>
        <PanelCard
          title={t('adminUsers_list_title')}
          subtitle={t('adminUsers_list_sub')}
          actions={<button onClick={loadUsers} className="rounded-2xl bg-slate-200 px-4 py-2 text-sm dark:bg-slate-800">{t('adminUsers_refresh')}</button>}
        >
          <div className="mb-4 flex gap-3">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('adminUsers_searchPlaceholder')} className="flex-1 rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700 dark:bg-slate-950" />
            <button onClick={() => { setPage(1); loadUsers() }} className="rounded-2xl bg-primary-600 px-4 py-3 text-sm text-white">{t('adminUsers_searchBtn')}</button>
          </div>
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400">
                  <th className="pb-3">{t('adminUsers_colEmail')}</th>
                  <th className="pb-3">{t('adminUsers_colRole')}</th>
                  <th className="pb-3">{t('adminUsers_colStatus')}</th>
                  <th className="pb-3">{t('adminUsers_colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t border-slate-200 dark:border-slate-800">
                    <td className="py-3">{user.email}</td>
                    <td className="py-3">{user.rol}</td>
                    <td className="py-3">{user.activo ? t('adminUsers_statusActive') : t('adminUsers_statusSuspended')}</td>
                    <td className="py-3">
                      <button onClick={() => toggleUser(user)} className="rounded-2xl bg-slate-200 px-3 py-2 dark:bg-slate-800">
                        {user.activo ? t('adminUsers_suspend') : t('adminUsers_activate')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-slate-500 dark:text-slate-400">{t('adminUsers_total', { count: total })}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">{t('adminUsers_prev')}</button>
              <button onClick={() => setPage((value) => value + 1)} disabled={page * 8 >= total} className="rounded-2xl bg-slate-200 px-3 py-2 disabled:opacity-40 dark:bg-slate-800">{t('adminUsers_next')}</button>
            </div>
          </div>
        </PanelCard>
      </div>
    </div>
  )
}
