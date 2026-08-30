import { useState } from 'react'
import api from '../lib/api'
import { useAuth } from '../state/AuthContext'

export default function ChatWidget() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Puedo ayudarte a interpretar simulaciones y el uso de la plataforma.' }])
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!message.trim()) return
    const newMessage = { role: 'user', content: message }
    setMessages((prev) => [...prev, newMessage])
    setLoading(true)
    setMessage('')
    try {
      const response = await api.post('/api/chat', { message: newMessage.content })
      setMessages((prev) => [...prev, { role: 'assistant', content: response.data.reply }])
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', content: error.response?.data?.detail || 'No fue posible responder en este momento.' }])
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return null
  }

  return (
    <div className="fixed bottom-5 right-5 z-30">
      {open ? (
        <div className="w-[min(92vw,360px)] overflow-hidden rounded-[1.75rem] border border-slate-200 bg-white shadow-panel dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between bg-slate-950 px-4 py-3 text-white">
            <div>
              <p className="font-medium">Asistente</p>
              <p className="text-xs text-slate-300">Chatbot conectado al backend</p>
            </div>
            <button onClick={() => setOpen(false)} className="rounded-full bg-white/10 px-3 py-1 text-sm">Cerrar</button>
          </div>
          <div className="max-h-80 space-y-3 overflow-auto p-4">
            {messages.map((item, index) => (
              <div key={index} className={`rounded-2xl px-4 py-3 text-sm ${item.role === 'user' ? 'ml-8 bg-primary-600 text-white' : 'mr-8 bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100'}`}>
                {item.content}
              </div>
            ))}
            {loading ? <div className="mr-8 rounded-2xl bg-slate-100 px-4 py-3 text-sm dark:bg-slate-800">Pensando...</div> : null}
          </div>
          <div className="flex gap-2 border-t border-slate-200 p-3 dark:border-slate-800">
            <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Escribe tu pregunta" className="flex-1 rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none dark:border-slate-700 dark:bg-slate-950" />
            <button onClick={handleSend} disabled={loading} className="rounded-2xl bg-primary-600 px-4 py-3 text-sm text-white">Enviar</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setOpen(true)} className="rounded-full bg-primary-600 px-5 py-3 text-sm font-medium text-white shadow-panel">Chat</button>
      )}
    </div>
  )
}
