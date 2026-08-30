import { Suspense, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../state/AuthContext'
import { useUi } from '../state/UiContext'
import SpinnerBlock from './SpinnerBlock'

const navItems = {
  cliente: [
    { to: '/client', label: 'Optimizacion' },
    { to: '/client/history', label: 'Historial' },
  ],
  admin: [
    { to: '/admin', label: 'Resumen' },
    { to: '/admin/users', label: 'Usuarios' },
    { to: '/admin/simulations', label: 'Simulaciones' },
  ],
}

export default function AppShell() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const { sidebarOpen, toggleSidebar, theme, toggleTheme } = useUi()
  const navigate = useNavigate()
  const items = navItems[user?.rol === 'admin' ? 'admin' : 'cliente']

  useEffect(() => {
    if (user?.rol === 'admin') {
      void import('../pages/AdminDashboard')
      void import('../pages/AdminUsersPage')
      void import('../pages/AdminSimulationsPage')
      return
    }

    if (user?.rol === 'cliente') {
      void import('../pages/ClientDashboard')
      void import('../pages/ClientHistoryPage')
    }
  }, [user?.rol])

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-100">
      <div className="flex min-h-screen">
        <aside className="relative z-20">
          <div
            className={`flex h-full flex-col border-r border-slate-200 bg-white/90 px-4 py-6 shadow-panel transition-all dark:border-slate-800 dark:bg-slate-900/85 ${sidebarOpen ? 'w-72' : 'w-24'}`}
          >
            <button
              onClick={toggleSidebar}
              className="mb-6 rounded-2xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
            >
              {sidebarOpen ? '<<' : '>>'}
            </button>
            <div className="mb-8">
              <p className="text-xs uppercase tracking-[0.3em] text-primary-600">{t('appName')}</p>
              {sidebarOpen && <h1 className="mt-2 text-xl font-semibold">{t('welcome')}</h1>}
            </div>
            <div className="rounded-3xl bg-slate-100 px-4 py-4 dark:bg-slate-800">
              <p className="truncate font-medium">{user?.email}</p>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">{user?.rol}</p>
            </div>
            <nav className="mt-8 space-y-2">
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/client' || item.to === '/admin'}
                  className={({ isActive }) =>
                    `block rounded-2xl px-4 py-3 text-sm transition ${isActive ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'}`
                  }
                >
                  {sidebarOpen ? item.label : item.label.slice(0, 1)}
                </NavLink>
              ))}
            </nav>
            <div className="mt-auto space-y-3 pt-6">
              <div className="flex gap-2">
                <button onClick={toggleTheme} className="flex-1 rounded-2xl bg-slate-200 px-3 py-2 text-sm dark:bg-slate-800">
                  {theme === 'dark' ? 'Light' : 'Dark'}
                </button>
                <button
                  onClick={() => i18n.changeLanguage(i18n.language === 'es' ? 'en' : 'es')}
                  className="rounded-2xl bg-slate-200 px-3 py-2 text-sm dark:bg-slate-800"
                >
                  {i18n.language.toUpperCase()}
                </button>
              </div>
              <button
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
                className="w-full rounded-2xl bg-primary-600 px-4 py-3 text-sm font-medium text-white"
              >
                {t('logout')}
              </button>
            </div>
          </div>
        </aside>
        <main className="flex-1 p-4 md:p-8">
          <Suspense fallback={<SpinnerBlock label="Cargando modulo" />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
