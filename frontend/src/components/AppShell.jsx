import { Suspense, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../state/AuthContext'
import { useUi } from '../state/UiContext'
import SpinnerBlock from './SpinnerBlock'

const navItems = {
  cliente: [
    { to: '/client', labelKey: 'nav_optimize' },
    { to: '/client/history', labelKey: 'nav_history' },
  ],
  admin: [
    { to: '/admin', labelKey: 'nav_summary' },
    { to: '/admin/users', labelKey: 'nav_users' },
    { to: '/admin/simulations', labelKey: 'nav_simulations' },
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
                  {sidebarOpen ? t(item.labelKey) : t(item.labelKey).slice(0, 1)}
                </NavLink>
              ))}
            </nav>
            <div className="mt-auto pt-6">
              <div className="flex gap-2">
                {/* Botón tema: luna = modo oscuro activo, sol = modo claro activo */}
                <button
                  onClick={toggleTheme}
                  title={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
                  className="flex flex-1 items-center justify-center rounded-2xl bg-slate-200 p-2.5 transition hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700"
                >
                  {theme === 'dark' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="4"/>
                      <line x1="12" y1="2" x2="12" y2="6"/>
                      <line x1="12" y1="18" x2="12" y2="22"/>
                      <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/>
                      <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
                      <line x1="2" y1="12" x2="6" y2="12"/>
                      <line x1="18" y1="12" x2="22" y2="12"/>
                      <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/>
                      <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                  )}
                </button>

                {/* Botón idioma: texto EN / ES */}
                <button
                  onClick={() => i18n.changeLanguage(i18n.language === 'es' ? 'en' : 'es')}
                  title={i18n.language === 'es' ? 'Switch to English' : 'Cambiar a Español'}
                  className="flex flex-1 items-center justify-center rounded-2xl bg-slate-200 p-2.5 text-sm font-bold tracking-wider transition hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700"
                >
                  {i18n.language === 'es' ? 'ES' : 'EN'}
                </button>

                {/* Botón salir: icono puerta con flecha */}
                <button
                  onClick={() => { logout(); navigate('/login') }}
                  title={t('logout')}
                  className="flex flex-1 items-center justify-center rounded-2xl bg-primary-600 p-2.5 text-white transition hover:bg-primary-700"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                    <polyline points="16 17 21 12 16 7"/>
                    <line x1="21" y1="12" x2="9" y2="12"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </aside>
        <main className="flex-1 p-4 md:p-8">
          <Suspense fallback={<SpinnerBlock label={t('loadingModule')} />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
