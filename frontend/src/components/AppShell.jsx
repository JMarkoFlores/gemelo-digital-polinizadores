import { Suspense, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../state/AuthContext'
import { useUi } from '../state/UiContext'
import SpinnerBlock from './SpinnerBlock'

const navItems = {
  cliente: [
    {
      to: '/client',
      labelKey: 'nav_optimize',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><circle cx="4" cy="14" r="2"/><circle cx="12" cy="10" r="2"/><circle cx="20" cy="16" r="2"/>
        </svg>
      ),
    },
    {
      to: '/client/history',
      labelKey: 'nav_history',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
        </svg>
      ),
    },
  ],
  admin: [
    {
      to: '/admin',
      labelKey: 'nav_summary',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>
        </svg>
      ),
    },
    {
      to: '/admin/users',
      labelKey: 'nav_users',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      ),
    },
    {
      to: '/admin/simulations',
      labelKey: 'nav_simulations',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
        </svg>
      ),
    },
    {
      to: '/admin/reports',
      labelKey: 'nav_reports',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
        </svg>
      ),
    },
  ],
}

export default function AppShell() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const { sidebarOpen, toggleSidebar, theme, toggleTheme } = useUi()
  const navigate = useNavigate()
  const location = useLocation()
  const items = navItems[user?.rol === 'admin' ? 'admin' : 'cliente'] || []

  useEffect(() => {
    if (user?.rol === 'admin') {
      void import('../pages/AdminDashboard')
      void import('../pages/AdminUsersPage')
      void import('../pages/AdminSimulationsPage')
      void import('../pages/AdminReportsPage')
      return
    }

    if (user?.rol === 'cliente') {
      void import('../pages/ClientDashboard')
      void import('../pages/ClientHistoryPage')
    }
  }, [user?.rol])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-100 flex flex-col md:flex-row">
      {/* Mobile Topbar */}
      <header className="md:hidden flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 sticky top-0 z-30 backdrop-blur-md dark:border-slate-800/90 dark:bg-slate-950/90">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a9 9 0 0 1 9 9c0 5-4 9-9 9s-9-4-9-9a9 9 0 0 1 9-9Z" />
              <path d="M12 7v5l3 3" />
              <path d="M7 14c1.5 1 3 1.5 5 1.5s3.5-.5 5-1.5" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-bold tracking-tight text-emerald-600 dark:text-emerald-400">{t('appName')}</p>
            <p className="text-[10px] uppercase font-semibold text-slate-400 dark:text-slate-500">{user?.rol || 'usuario'}</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700 transition hover:bg-slate-200 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {theme === 'dark' ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>

          <button
            onClick={toggleSidebar}
            aria-label="Open navigation menu"
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700 transition hover:bg-slate-200 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/>
            </svg>
          </button>
        </div>
      </header>

      {/* Backdrop for Mobile Drawer */}
      {sidebarOpen && (
        <div
          onClick={toggleSidebar}
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden transition-opacity"
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`fixed md:sticky top-0 z-50 md:z-20 h-screen shrink-0 transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0 w-72' : '-translate-x-full md:translate-x-0 md:w-20'
        }`}
      >
        <div className="flex h-full flex-col border-r border-slate-200/80 bg-white/95 px-3.5 py-5 shadow-panel backdrop-blur-md dark:border-slate-800/80 dark:bg-slate-900/95">
          
          {/* Header & Logo */}
          <div className="flex items-center justify-between gap-3 mb-6 px-1">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a9 9 0 0 1 9 9c0 5-4 9-9 9s-9-4-9-9a9 9 0 0 1 9-9Z" />
                  <path d="M12 7v5l3 3" />
                  <path d="M7 14c1.5 1 3 1.5 5 1.5s3.5-.5 5-1.5" />
                </svg>
              </div>
              {sidebarOpen && (
                <div className="min-w-0">
                  <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-emerald-600 dark:text-emerald-400">Gemelos Digitales</p>
                  <p className="truncate text-xs font-semibold text-slate-800 dark:text-slate-200">Polinizadores</p>
                </div>
              )}
            </div>

            <button
              onClick={toggleSidebar}
              title={sidebarOpen ? 'Colapsar menú' : 'Expandir menú'}
              className="hidden md:flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200/80 bg-slate-50 text-slate-600 transition hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {sidebarOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
              )}
            </button>

            {/* Mobile close cross */}
            <button
              onClick={toggleSidebar}
              className="md:hidden flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          {/* User badge */}
          {sidebarOpen ? (
            <div className="mb-5 rounded-2xl border border-slate-200/60 bg-slate-100/70 p-3 dark:border-slate-800/60 dark:bg-slate-800/50">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white uppercase">
                  {user?.email ? user.email.slice(0, 2) : 'US'}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-slate-900 dark:text-slate-100">{user?.email}</p>
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    {user?.rol || 'usuario'}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="mb-4 flex justify-center">
              <div
                title={`${user?.email} (${user?.rol})`}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white uppercase shadow-sm"
              >
                {user?.email ? user.email.slice(0, 2) : 'US'}
              </div>
            </div>
          )}

          {/* Nav List */}
          <nav className="space-y-1.5 flex-1">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/client' || item.to === '/admin'}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-600 text-white shadow-sm font-semibold'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/70 dark:hover:text-white'
                  } ${!sidebarOpen ? 'justify-center' : ''}`
                }
                title={!sidebarOpen ? t(item.labelKey) : undefined}
              >
                <span className="shrink-0">{item.icon}</span>
                {sidebarOpen && <span className="truncate">{t(item.labelKey)}</span>}
              </NavLink>
            ))}
          </nav>

          {/* Footer Controls */}
          <div className="pt-4 border-t border-slate-200/80 dark:border-slate-800/80 space-y-2">
            <div className={`flex gap-1.5 ${!sidebarOpen ? 'flex-col items-center' : ''}`}>
              {/* Theme toggle */}
              <button
                onClick={toggleTheme}
                title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
                className="flex-1 flex items-center justify-center rounded-xl bg-slate-100 p-2 text-slate-600 transition hover:bg-slate-200 hover:text-slate-900 dark:bg-slate-800/70 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white h-9"
              >
                {theme === 'dark' ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                  </svg>
                )}
              </button>

              {/* Language toggle */}
              <button
                onClick={() => i18n.changeLanguage(i18n.language === 'es' ? 'en' : 'es')}
                title={i18n.language === 'es' ? 'Switch to English' : 'Cambiar a Español'}
                className="flex-1 flex items-center justify-center rounded-xl bg-slate-100 p-2 text-xs font-bold tracking-wider text-slate-700 transition hover:bg-slate-200 hover:text-slate-900 dark:bg-slate-800/70 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white h-9"
              >
                {i18n.language === 'es' ? 'ES' : 'EN'}
              </button>

              {/* Logout button */}
              <button
                onClick={() => { logout(); navigate('/login') }}
                title={t('logout')}
                className="flex-1 flex items-center justify-center rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 p-2 transition hover:bg-rose-500 hover:text-white dark:hover:bg-rose-600 dark:hover:text-white h-9"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
              </button>
            </div>
          </div>

        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8">
        <Suspense fallback={<SpinnerBlock label={t('loadingModule')} />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
