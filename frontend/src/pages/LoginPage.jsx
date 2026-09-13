import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import AuthCard from '../components/AuthCard'
import FormField from '../components/FormField'
import { useAuth } from '../state/AuthContext'

export default function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('Admin12345!')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const user = await login({ email, password })
      navigate(user.rol === 'admin' ? '/admin' : '/client')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible iniciar sesión.')
    } finally {
      setSubmitting(false)
    }
  }

  const fillCredentials = (userEmail, userPass) => {
    setEmail(userEmail)
    setPassword(userPass)
    setError('')
  }

  return (
    <AuthCard
      title={t('login')}
      subtitle="Accede al gemelo digital para modelado agroecológico y optimización de paisajes."
      footer={
        <div className="flex items-center justify-between">
          <span className="text-slate-400">¿No tienes cuenta?</span>
          <Link to="/register" className="font-semibold text-emerald-400 hover:text-emerald-300 transition">
            Crear cuenta de cliente &rarr;
          </Link>
        </div>
      }
    >
      {/* Quick demo account switcher chips */}
      <div className="mb-5 rounded-2xl bg-slate-950/60 p-3 border border-slate-800/80">
        <p className="text-[11px] font-medium text-slate-400 mb-2 uppercase tracking-wider">Acceso rápido de prueba:</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => fillCredentials('admin@example.com', 'Admin12345!')}
            className={`flex-1 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition ${
              email.includes('admin')
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 border border-transparent'
            }`}
          >
            Modo Admin
          </button>
          <button
            type="button"
            onClick={() => fillCredentials('cliente@agricola.pe', 'Cliente123!')}
            className={`flex-1 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition ${
              !email.includes('admin')
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 border border-transparent'
            }`}
          >
            Modo Cliente
          </button>
        </div>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField label={t('email')} type="email" value={email} onChange={setEmail} required />
        <FormField label={t('password')} type="password" value={password} onChange={setPassword} required />

        {error ? (
          <div className="flex items-center gap-2 rounded-xl bg-rose-500/10 border border-rose-500/20 px-3.5 py-2.5 text-xs text-rose-300">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-rose-400">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{error}</span>
          </div>
        ) : null}

        <button
          disabled={submitting}
          className="group relative flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 font-semibold text-white shadow-md transition hover:bg-emerald-500 active:scale-[0.99] disabled:opacity-60 disabled:pointer-events-none"
        >
          {submitting ? (
            <>
              <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Ingresando...</span>
            </>
          ) : (
            <>
              <span>{t('login')}</span>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-hover:translate-x-0.5">
                <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
              </svg>
            </>
          )}
        </button>
      </form>
    </AuthCard>
  )
}
