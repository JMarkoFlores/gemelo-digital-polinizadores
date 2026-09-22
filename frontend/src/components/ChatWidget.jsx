import { useState, useRef, useEffect } from 'react'
import api from '../lib/api'
import { useAuth } from '../state/AuthContext'

export default function ChatWidget() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        '¡Hola! Soy tu asistente del Gemelo Digital Agroecológico. Puedo ayudarte con datos reales de simulaciones, variables agronómicas (pesticidas, polinizadores, rendimiento) y métricas de la plataforma.',
    },
  ])
  const [loading, setLoading] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  // Tooltip emergente de bienvenida (se muestra al inicio si no se ha descartado)
  const [showTooltip, setShowTooltip] = useState(() => {
    return sessionStorage.getItem('gemelos_chat_tooltip_closed') !== 'true'
  })

  // Animación sutil de pulso/atención inicial (se detiene tras la primera interacción)
  const [hasInteracted, setHasInteracted] = useState(() => {
    return sessionStorage.getItem('gemelos_chat_interacted') === 'true'
  })

  const messagesEndRef = useRef(null)

  // Auto-scroll al recibir o enviar mensajes
  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, loading, open])

  // Descartar tooltip manualmente
  const handleDismissTooltip = (e) => {
    e.stopPropagation()
    setShowTooltip(false)
    sessionStorage.setItem('gemelos_chat_tooltip_closed', 'true')
    handleMarkInteracted()
  }

  // Marcar que el usuario ya interactuó
  const handleMarkInteracted = () => {
    if (!hasInteracted) {
      setHasInteracted(true)
      sessionStorage.setItem('gemelos_chat_interacted', 'true')
    }
  }

  const handleOpenChat = () => {
    setOpen(true)
    setShowTooltip(false)
    sessionStorage.setItem('gemelos_chat_tooltip_closed', 'true')
    handleMarkInteracted()
  }

  const sendMessage = async (textToSend) => {
    const text = (textToSend || message).trim()
    if (!text || loading) return

    const newMessage = { role: 'user', content: text }
    const currentHistory = messages
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content }))
      .slice(-8)

    setMessages((prev) => [...prev, newMessage])
    setLoading(true)
    setMessage('')
    handleMarkInteracted()

    try {
      const response = await api.post('/api/chat', {
        message: text,
        history: currentHistory,
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: response.data.reply }])
    } catch (error) {
      const errorMsg =
        error.response?.data?.detail || 'No fue posible obtener respuesta del asistente en este momento.'
      setMessages((prev) => [...prev, { role: 'assistant', content: errorMsg }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!user) {
    return null
  }

  // Sugerencias de preguntas rápidas según el rol del usuario
  const quickQuestions =
    user.rol === 'admin'
      ? [
          '¿Cuántos usuarios activos hay en el sistema?',
          '¿Qué resultados se obtuvieron de la simulación #1?',
          '¿Cuál es la región con más simulaciones?',
        ]
      : [
          '¿Qué resultados se obtuvieron de la simulación #1?',
          '¿Cuántas simulaciones he realizado?',
          '¿Cuál es la región con más simulaciones?',
        ]

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {open ? (
        /* VENTANA DEL CHATBOT ABIERTA */
        <div className="flex h-[520px] max-h-[85vh] w-[min(94vw,380px)] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl transition-all duration-300 dark:border-slate-800 dark:bg-slate-900">
          {/* Cabecera del Chat */}
          <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-4 py-3.5 text-white">
            <div className="flex items-center gap-3">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 shadow-md">
                {/* Ícono Asistente / Bot */}
                <svg className="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 8V4H8" />
                  <rect width="16" height="12" x="4" y="8" rx="2" />
                  <path d="M2 14h2" />
                  <path d="M20 14h2" />
                  <path d="M15 13v2" />
                  <path d="M9 13v2" />
                </svg>
                {/* Punto online */}
                <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex h-3 w-3 rounded-full border-2 border-slate-950 bg-emerald-400"></span>
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-white">Asistente Gemelo Digital</p>
                  <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
                    IA Activa
                  </span>
                </div>
                <p className="text-xs text-slate-400">Datos en tiempo real de la base de datos</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-slate-300 transition hover:bg-white/20 hover:text-white"
              title="Cerrar chat"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Área de Mensajes */}
          <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
            {messages.map((item, index) => (
              <div
                key={index}
                className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 leading-relaxed shadow-sm ${
                    item.role === 'user'
                      ? 'rounded-br-sm bg-gradient-to-r from-emerald-600 to-teal-600 text-white'
                      : 'rounded-bl-sm border border-slate-100 bg-slate-100 text-slate-800 dark:border-slate-800/60 dark:bg-slate-800 dark:text-slate-100 whitespace-pre-wrap'
                  }`}
                >
                  {item.content}
                </div>
              </div>
            ))}

            {/* Sugerencias Rápidas al inicio */}
            {messages.length === 1 && (
              <div className="mt-3 space-y-2 pt-2">
                <p className="text-xs font-medium text-slate-400 dark:text-slate-500">
                  Preguntas frecuentes sugeridas:
                </p>
                <div className="flex flex-col gap-1.5">
                  {quickQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => sendMessage(q)}
                      className="rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-2 text-left text-xs font-medium text-emerald-800 transition hover:bg-emerald-100 dark:border-emerald-900/40 dark:bg-emerald-950/40 dark:text-emerald-300 dark:hover:bg-emerald-900/60"
                    >
                      💡 {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Loader de pensamiento */}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-slate-100 bg-slate-100 px-4 py-2.5 text-xs text-slate-600 dark:border-slate-800/60 dark:bg-slate-800 dark:text-slate-300">
                  <span className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-500"></span>
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-500 [animation-delay:0.2s]"></span>
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-500 [animation-delay:0.4s]"></span>
                  </span>
                  <span>Consultando datos del sistema...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Pie de entrada del Chat */}
          <div className="border-t border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-950/80">
            <div className="flex items-center gap-2">
              <input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Escribe tu pregunta sobre simulaciones..."
                disabled={loading}
                className="flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500"
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !message.trim()}
                className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-md transition hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
                title="Enviar mensaje"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
            <div className="mt-1.5 flex items-center justify-between px-1 text-[11px] text-slate-400 dark:text-slate-500">
              <span>Enter para enviar</span>
              <span>Rol: {user.rol}</span>
            </div>
          </div>
        </div>
      ) : (
        /* BOTÓN FLOTANTE MEJORADO CON TOOLTIP / LABEL DE BIENVENIDA */
        <div
          className="relative flex items-center justify-end gap-3"
          onMouseEnter={() => {
            setIsHovered(true)
            handleMarkInteracted()
          }}
          onMouseLeave={() => setIsHovered(false)}
        >
          {/* Tooltip / Globo de Diálogo Flotante */}
          {(showTooltip || isHovered) && (
            <div
              className="relative flex items-center gap-2 rounded-2xl border border-emerald-200 bg-white/95 px-3.5 py-2.5 shadow-xl backdrop-blur-sm transition-all duration-300 dark:border-emerald-800/60 dark:bg-slate-900/95"
              style={{ animation: 'fadeIn 0.2s ease-out' }}
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                    Asistente Agroecológico
                  </span>
                  <span className="flex h-2 w-2 rounded-full bg-emerald-500"></span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  ¿Dudas o preguntas? Chatea conmigo 👋
                </p>
              </div>

              {/* Botón descartar tooltip */}
              <button
                onClick={handleDismissTooltip}
                className="ml-1 rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                title="Cerrar sugerencia"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>

              {/* Flechita apuntando al botón */}
              <div className="absolute -right-2 top-1/2 -translate-y-1/2 border-y-4 border-l-8 border-y-transparent border-l-white dark:border-l-slate-900"></div>
            </div>
          )}

          {/* Botón Circular Principal */}
          <button
            onClick={handleOpenChat}
            title="Abrir Asistente IA del Gemelo Digital"
            className={`group relative flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-tr from-emerald-700 via-emerald-600 to-teal-500 text-white shadow-panel transition-all duration-300 hover:scale-105 hover:shadow-glow active:scale-95 ${
              !hasInteracted ? 'animate-pulse ring-4 ring-emerald-400/40' : ''
            }`}
          >
            {/* Ícono Vectorial Claro de Chat / Mensajes con Chispas IA */}
            <div className="relative">
              {/* Burbuja de diálogo principal con líneas */}
              <svg
                className="h-7 w-7 transition-transform duration-300 group-hover:scale-110"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" fill="currentColor" fillOpacity="0.15" />
                {/* 3 puntos de conversación */}
                <circle cx="9" cy="10" r="1" fill="currentColor" />
                <circle cx="12" cy="10" r="1" fill="currentColor" />
                <circle cx="15" cy="10" r="1" fill="currentColor" />
              </svg>

              {/* Chispitas IA superpuestas en la esquina */}
              <svg
                className="absolute -right-1.5 -top-1.5 h-3.5 w-3.5 text-amber-300"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />
              </svg>
            </div>

            {/* Badge de estado en línea (punto verde brillante en la esquina) */}
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-80"></span>
              <span className="relative inline-flex h-4 w-4 rounded-full border-2 border-white bg-emerald-400 shadow-sm dark:border-slate-900"></span>
            </span>
          </button>
        </div>
      )}
    </div>
  )
}
