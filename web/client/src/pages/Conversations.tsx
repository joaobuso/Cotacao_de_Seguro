import React, { useState, useEffect } from 'react'
import { Link } from 'wouter'
import Layout from '../components/Layout'
import { MessageSquare, Phone, Clock, ChevronRight, RefreshCw, Search } from 'lucide-react'

interface Conversation {
  phone: string
  phone_display: string
  last_message: string
  last_timestamp: string | null
  message_count: number
  needs_human: boolean
  has_human_response: boolean
}

export default function Conversations() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/conversations', { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setConversations(data)
      }
    } catch (err) {
      console.error('Erro ao buscar conversas:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConversations()
    const interval = setInterval(fetchConversations, 15000)
    return () => clearInterval(interval)
  }, [])

  const filtered = conversations.filter(c =>
    c.phone_display.toLowerCase().includes(search.toLowerCase()) ||
    c.phone.includes(search) ||
    c.last_message.toLowerCase().includes(search.toLowerCase())
  )

  const formatTimestamp = (ts: string | null) => {
    if (!ts) return ''
    try {
      const date = new Date(ts)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)

      if (diffMins < 1) return 'Agora'
      if (diffMins < 60) return `${diffMins}min`
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h`
      return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
    } catch {
      return ''
    }
  }

  return (
    <Layout title="Conversas" subtitle="Todas as conversas via WhatsApp">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por telefone ou mensagem..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>
        <button
          onClick={() => { setLoading(true); fetchConversations() }}
          className="flex items-center gap-2 px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all text-slate-600 ml-4"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {/* Lista */}
      {loading && conversations.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
          <MessageSquare size={48} className="mx-auto text-slate-300 mb-4" />
          <h3 className="text-lg font-medium text-slate-600">Nenhuma conversa encontrada</h3>
          <p className="text-sm text-slate-400 mt-1">As conversas aparecerão aqui quando clientes enviarem mensagens.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
          {filtered.map((conv) => (
            <Link key={conv.phone} href={`/portal/conversations/${encodeURIComponent(conv.phone)}`}>
              <div className="flex items-center px-6 py-4 hover:bg-slate-50 cursor-pointer transition-all group">
                {/* Avatar */}
                <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                  conv.needs_human ? 'bg-red-100' : 'bg-green-100'
                }`}>
                  <Phone size={20} className={conv.needs_human ? 'text-red-600' : 'text-green-600'} />
                </div>

                {/* Info */}
                <div className="ml-4 flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-900">{conv.phone_display}</h3>
                    <div className="flex items-center gap-2">
                      {conv.needs_human && (
                        <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                          Humano
                        </span>
                      )}
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock size={12} />
                        {formatTimestamp(conv.last_timestamp)}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-500 truncate mt-0.5">{conv.last_message}</p>
                  <p className="text-xs text-slate-400 mt-1">{conv.message_count} mensagens</p>
                </div>

                {/* Arrow */}
                <ChevronRight size={20} className="text-slate-300 group-hover:text-slate-500 ml-4 flex-shrink-0 transition-colors" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </Layout>
  )
}
