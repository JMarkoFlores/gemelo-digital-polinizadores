import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import AuthCard from '../components/AuthCard'
import FormField from '../components/FormField'
import { useAuth } from '../state/AuthContext'

export default function RegisterPage() {
  const { t } = useTranslation()
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await register({ email, password, rol: 'cliente' })
      navigate('/client')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible crear la cuenta.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title={t('register')}
      subtitle="Crea una cuenta de cliente para diseñar escenarios y correr optimizaciones de paisaje."
      footer={
        <div className="flex items-center justify-between">
          <span className="text-slate-400">¿Ya tienes una cuenta?</span>
          <Link to="/login" className="font-semibold text-emerald-400 hover:text-emerald-300 transition">
            Iniciar sesión &rarr;
          </Link>
        </div>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField label={t('email')} type="email" value={email} onChange={setEmail} placeholder="tu.correo@organizacion.com" required />
        <FormField label={t('password')} type="password" value={password} onChange={setPassword} placeholder="Mínimo 8 caracteres" required />
        
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
              <span>Creando cuenta...</span>
            </>
          ) : (
            <>
              <span>{t('register')}</span>
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
