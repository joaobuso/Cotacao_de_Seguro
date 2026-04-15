import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'wouter'
import Layout from '../components/Layout'
import {
  ArrowLeft,
  Send,
  RefreshCw,
  User,
  Bot,
  UserCheck,
  CheckCircle,
  Clock
} from 'lucide-react'

interface Message {
  sender: string
  message: string
  timestamp: string | null
}

interface ConversationData {
  phone: string
  phone_display: string
  messages: Message[]
  client_data: Record<string, string> | null
}

interface Props {
  phone: string
}

const QUICK_MESSAGES = [
  { label: 'Saudação', text: 'Olá! Sou especialista da Equinos Seguros. Como posso ajudá-lo?' },
  { label: 'Solicitar dados', text: 'Preciso de mais informações para sua cotação. Poderia me enviar os dados do animal?' },
  { label: 'Processando', text: 'Sua cotação está sendo processada! Em breve enviarei o resultado.' },
  { label: 'Encerrar', text: 'Obrigado por escolher a Equinos Seguros! Se precisar de algo mais, estamos à disposição.' },
]

export default function ConversationDetail({ phone }: Props) {
  const [data, setData] = useState<ConversationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [alert, setAlert] = useState<{ type: string; text: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const decodedPhone = decodeURIComponent(phone)

  const fetchConversation = async () => {
    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(decodedPhone)}`, {
        credentials: 'include'
      })
      if (res.ok) {
        const result = await res.json()
        setData(result)
      }
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConversation()
    const interval = setInterval(fetchConversation, 10000)
    return () => clearInterval(interval)
  }, [decodedPhone])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [data?.messages])

  const sendMessage = async (text: string) => {
    if (!text.trim()) return

    setSending(true)
    setAlert(null)

    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(decodedPhone)}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ message: text })
      })

      const result = await res.json()

      if (result.success) {
        setAlert({ type: 'success', text: 'Mensagem enviada com sucesso!' })
        setMessage('')
        setTimeout(fetchConversation, 1500)
      } else {
        setAlert({ type: 'error', text: result.message || 'Erro ao enviar mensagem' })
      }
    } catch (err) {
      setAlert({ type: 'error', text: 'Erro de conexão' })
    } finally {
      setSending(false)
    }
  }

  const completeQuotation = async () => {
    if (!confirm('Deseja finalizar a cotação para este cliente?')) return

    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(decodedPhone)}/complete`, {
        method: 'POST',
        credentials: 'include'
      })

      const result = await res.json()

      if (result.success) {
        setAlert({ type: 'success', text: 'Cotação finalizada com sucesso!' })
        setTimeout(fetchConversation, 1500)
      } else {
        setAlert({ type: 'error', text: result.error || 'Erro ao finalizar cotação' })
      }
    } catch (err) {
      setAlert({ type: 'error', text: 'Erro de conexão' })
    }
  }

  const formatTime = (ts: string | null) => {
    if (!ts) return ''
    try {
      return new Date(ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  const formatDate = (ts: string | null) => {
    if (!ts) return ''
    try {
      return new Date(ts).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
    } catch {
      return ''
    }
  }

  const getSenderInfo = (sender: string) => {
    switch (sender) {
      case 'user':
        return { icon: User, label: 'Cliente', bg: 'bg-blue-50', border: 'border-l-blue-500', text: 'text-blue-700' }
      case 'bot':
        return { icon: Bot, label: 'Bot', bg: 'bg-green-50', border: 'border-l-green-500', text: 'text-green-700' }
      default:
        return { icon: UserCheck, label: 'Agente', bg: 'bg-orange-50', border: 'border-l-orange-500', text: 'text-orange-700' }
    }
  }

  return (
    <Layout
      title={data?.phone_display || 'Conversa'}
      subtitle={`Telefone: ${decodedPhone}`}
    >
      <div className="mb-4">
        <Link href="/portal/conversations">
          <span className="inline-flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 cursor-pointer">
            <ArrowLeft size={16} />
            Voltar para conversas
          </span>
        </Link>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat Panel */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 flex flex-col" style={{ height: '700px' }}>
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">Conversa</h3>
              <button
                onClick={() => { setLoading(true); fetchConversation() }}
                className="text-slate-400 hover:text-slate-600"
              >
                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>

            {/* Alert */}
            {alert && (
              <div className={`mx-6 mt-4 px-4 py-2 rounded-lg text-sm ${
                alert.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {alert.text}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {data?.messages.map((msg, i) => {
                const info = getSenderInfo(msg.sender)
                const Icon = info.icon
                return (
                  <div key={i} className={`${info.bg} border-l-4 ${info.border} rounded-lg p-4`}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon size={16} className={info.text} />
                      <span className={`text-sm font-semibold ${info.text}`}>{info.label}</span>
                      <span className="text-xs text-slate-400 ml-auto flex items-center gap-1">
                        <Clock size={12} />
                        {formatDate(msg.timestamp)} {formatTime(msg.timestamp)}
                      </span>
                    </div>
                    <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                      {msg.message}
                    </div>
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-6 py-4 border-t border-slate-200">
              <div className="flex gap-3">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage(message)
                    }
                  }}
                  placeholder="Digite sua resposta..."
                  className="flex-1 px-4 py-3 border border-slate-200 rounded-lg text-sm resize-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  rows={2}
                />
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => sendMessage(message)}
                    disabled={sending || !message.trim()}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium transition-all"
                  >
                    <Send size={16} />
                    Enviar
                  </button>
                  <button
                    onClick={completeQuotation}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2 text-sm font-medium transition-all"
                  >
                    <CheckCircle size={16} />
                    Finalizar
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar - Client Data + Quick Messages */}
          <div className="space-y-6">
            {/* Client Data */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Dados do Cliente</h3>
              {data?.client_data && Object.keys(data.client_data).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(data.client_data).map(([key, value]) => (
                    <div key={key} className="border-b border-slate-100 pb-2">
                      <p className="text-xs text-slate-500 uppercase tracking-wide">
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p className="text-sm font-medium text-slate-900">{value}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">Nenhum dado coletado ainda.</p>
              )}
            </div>

            {/* Quick Messages */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Mensagens Rápidas</h3>
              <div className="space-y-2">
                {QUICK_MESSAGES.map((qm, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(qm.text)}
                    disabled={sending}
                    className="w-full text-left px-3 py-2 text-sm bg-slate-50 hover:bg-slate-100 rounded-lg transition-all disabled:opacity-50"
                  >
                    {qm.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
