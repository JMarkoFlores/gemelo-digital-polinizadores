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
      setError(requestError.response?.data?.detail || 'No fue posible iniciar sesion')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title={t('login')}
      subtitle="Accede a la plataforma base para el flujo de investigacion y administracion."
      footer={<Link to="/register" className="text-primary-400">Crear una cuenta de cliente</Link>}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField label={t('email')} type="email" value={email} onChange={setEmail} />
        <FormField label={t('password')} type="password" value={password} onChange={setPassword} />
        {error ? <p className="rounded-2xl bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{error}</p> : null}
        <button disabled={submitting} className="w-full rounded-2xl bg-primary-600 px-4 py-3 font-medium text-white disabled:opacity-60">
          {submitting ? 'Ingresando...' : t('login')}
        </button>
      </form>
    </AuthCard>
  )
}
