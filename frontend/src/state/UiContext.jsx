import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const UiContext = createContext(null)

export function UiProvider({ children }) {
  const [theme, setTheme] = useState(localStorage.getItem('gemelos-theme') || 'dark')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    document.body.classList.toggle('light', theme === 'light')
    localStorage.setItem('gemelos-theme', theme)
  }, [theme])

  const value = useMemo(
    () => ({
      theme,
      sidebarOpen,
      toggleTheme: () => setTheme((value) => (value === 'dark' ? 'light' : 'dark')),
      toggleSidebar: () => setSidebarOpen((value) => !value),
    }),
    [sidebarOpen, theme],
  )

  return <UiContext.Provider value={value}>{children}</UiContext.Provider>
}

export function useUi() {
  return useContext(UiContext)
}
