import React, { useEffect, useState, useRef } from 'react'
import { Link } from 'wouter'
import { ArrowLeft, Send, CheckCircle, User, Bot, Clock } from 'lucide-react'

interface Message {
  sender: string
  message: string
  timestamp: string | null
}

interface ConvData {
  phone: string
  phone_display: string
  messages: Message[]
  client_data: Record<string, string> | null
}

interface Props {
  phone: string
}

const quickReplies = [
  'Olá! Como posso ajudar?',
  'Vou verificar isso para você.',
  'Sua cotação está sendo processada.',
  'Por favor, aguarde um momento.',
  'Obrigado pelo contato!',
]

function fmtTime(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export default function ConversationDetail({ phone }: Props) {
  const [data, setData] = useState<ConvData | null>(null)
  const [msg, setMsg] = useState('')
  const [sending, setSending] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [alert, setAlert] = useState<{ type: string; text: string } | null>(null)
  const chatEnd = useRef<HTMLDivElement>(null)

  const load = () => {
    fetch(`/api/conversations/${encodeURIComponent(phone)}`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: ConvData | null) => { if (d) setData(d) })
      .catch(() => {})
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 10000)
    return () => clearInterval(t)
  }, [phone])

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [data?.messages.length])

  const sendMsg = async (text: string) => {
    if (!text.trim()) return
    setSending(true)
    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(phone)}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ message: text }),
      })
      const d = await res.json()
      if (d.success) {
        setMsg('')
        setAlert({ type: 'ok', text: 'Mensagem enviada!' })
        load()
      } else {
        setAlert({ type: 'err', text: d.message || 'Erro ao enviar' })
      }
    } catch {
      setAlert({ type: 'err', text: 'Erro de conexão' })
    }
    setSending(false)
    setTimeout(() => setAlert(null), 3000)
  }

  const complete = async () => {
    if (!window.confirm('Finalizar cotação para este cliente?')) return
    setCompleting(true)
    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(phone)}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })
      const d = await res.json()
      if (d.success) {
        setAlert({ type: 'ok', text: 'Cotação finalizada!' })
        load()
      } else {
        setAlert({ type: 'err', text: d.error || 'Erro' })
      }
    } catch {
      setAlert({ type: 'err', text: 'Erro de conexão' })
    }
    setCompleting(false)
    setTimeout(() => setAlert(null), 3000)
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
          <Link href="/conversations">
            <div className="p-2 hover:bg-slate-100 rounded-lg cursor-pointer transition-all">
              <ArrowLeft size={20} className="text-slate-600" />
            </div>
          </Link>
          <div className="w-10 h-10 bg-green-100 text-green-700 rounded-full flex items-center justify-center font-bold text-sm">
            {data.phone_display.slice(-2)}
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-slate-900">{data.phone_display}</h2>
            <p className="text-xs text-slate-500">{data.messages.length} mensagens</p>
          </div>
          <button
            onClick={complete}
            disabled={completing}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-all"
          >
            <CheckCircle size={16} />
            {completing ? 'Finalizando...' : 'Finalizar Cotação'}
          </button>
        </header>

        {alert && (
          <div className={`mx-6 mt-3 px-4 py-2 rounded-lg text-sm ${alert.type === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {alert.text}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {data.messages.map((m, i) => {
            const isBot = m.sender === 'bot' || m.sender === 'agent'
            return (
              <div key={i} className={`flex ${isBot ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] rounded-2xl px-4 py-3 ${isBot ? 'bg-primary-600 text-white rounded-br-md' : 'bg-white border border-slate-200 text-slate-900 rounded-bl-md'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    {isBot ? <Bot size={12} /> : <User size={12} />}
                    <span className="text-xs opacity-75">{m.sender === 'agent' ? 'Agente' : m.sender === 'bot' ? 'Bot' : 'Cliente'}</span>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{m.message}</p>
                  {m.timestamp && (
                    <p className={`text-xs mt-1 flex items-center gap-1 ${isBot ? 'text-white/60' : 'text-slate-400'}`}>
                      <Clock size={10} />
                      {fmtTime(m.timestamp)}
                    </p>
                  )}
                </div>
              </div>
            )
          })}
          <div ref={chatEnd} />
        </div>

        <div className="px-6 py-2 flex gap-2 overflow-x-auto">
          {quickReplies.map((qr) => (
            <button key={qr} onClick={() => sendMsg(qr)} className="flex-shrink-0 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-full text-xs transition-all">
              {qr}
            </button>
          ))}
        </div>

        <div className="bg-white border-t border-slate-200 px-6 py-4">
          <form onSubmit={(e) => { e.preventDefault(); sendMsg(msg) }} className="flex gap-3">
            <input
              type="text"
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              placeholder="Digite uma mensagem..."
              className="flex-1 px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
            <button type="submit" disabled={sending || !msg.trim()} className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition-all flex items-center gap-2">
              <Send size={18} />
              Enviar
            </button>
          </form>
        </div>
      </div>

      <aside className="w-80 bg-white border-l border-slate-200 p-6 overflow-y-auto hidden lg:block">
        <h3 className="font-semibold text-slate-900 mb-4">Dados do Cliente</h3>
        {data.client_data ? (
          <div className="space-y-3">
            {Object.entries(data.client_data).map(([k, v]) => (
              <div key={k} className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-500 uppercase tracking-wider">{k}</p>
                <p className="text-sm font-medium text-slate-900 mt-0.5">{String(v)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Nenhum dado coletado ainda.</p>
        )}
      </aside>
    </div>
  )
}
