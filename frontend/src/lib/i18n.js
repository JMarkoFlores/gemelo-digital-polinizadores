import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  es: {
    translation: {
      appName: 'Gemelos Digitales',
      login: 'Iniciar sesion',
      register: 'Crear cuenta',
      email: 'Correo',
      password: 'Contrasena',
      logout: 'Salir',
      optimize: 'Optimizar paisaje',
      history: 'Historial',
      admin: 'Administracion',
      clientDashboard: 'Panel del investigador',
      adminDashboard: 'Panel de administracion',
      welcome: 'Plataforma de analisis y optimizacion agroecologica',
    },
  },
  en: {
    translation: {
      appName: 'Digital Twins',
      login: 'Sign in',
      register: 'Create account',
      email: 'Email',
      password: 'Password',
      logout: 'Logout',
      optimize: 'Optimize landscape',
      history: 'History',
      admin: 'Admin',
      clientDashboard: 'Research dashboard',
      adminDashboard: 'Administration dashboard',
      welcome: 'Agroecological analysis and optimization platform',
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: 'es',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n
