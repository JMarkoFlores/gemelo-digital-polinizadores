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
      setError(requestError.response?.data?.detail || 'No fue posible crear la cuenta')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title={t('register')}
      subtitle="Crea una cuenta de cliente para preparar escenarios y simulaciones."
      footer={<Link to="/login" className="text-primary-400">Volver al inicio de sesion</Link>}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField label={t('email')} type="email" value={email} onChange={setEmail} />
        <FormField label={t('password')} type="password" value={password} onChange={setPassword} />
        {error ? <p className="rounded-2xl bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{error}</p> : null}
        <button disabled={submitting} className="w-full rounded-2xl bg-primary-600 px-4 py-3 font-medium text-white disabled:opacity-60">
          {submitting ? 'Creando...' : t('register')}
        </button>
      </form>
    </AuthCard>
  )
}
