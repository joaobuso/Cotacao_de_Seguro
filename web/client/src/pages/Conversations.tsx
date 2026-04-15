import React, { useEffect, useState, useCallback } from 'react'
import { Link } from 'wouter'
import Layout from '../components/Layout'
import { Search, RefreshCw, MessageSquare, Clock, ChevronRight } from 'lucide-react'

interface Conversation {
  phone: string
  phone_display: string
  last_message: string
  last_timestamp: string | null
  message_count: number
  needs_human: boolean
  has_human_response: boolean
}

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'agora'
  if (mins < 60) return `${mins}min`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  return `${Math.floor(hrs / 24)}d`
}

export default function Conversations() {
  const [list, setList] = useState<Conversation[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    fetch('/api/conversations', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : []))
      .then((d: Conversation[]) => setList(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [load])

  const filtered = list.filter(
    (c) =>
      c.phone.includes(search) ||
      c.phone_display.toLowerCase().includes(search.toLowerCase()) ||
      (c.last_message || '').toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <Layout title="Conversas" subtitle="Todas as conversas via WhatsApp">
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
          onClick={() => { setLoading(true); load() }}
          className="flex items-center gap-2 px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all text-slate-600 ml-4"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {loading && list.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          <MessageSquare size={48} className="mx-auto mb-4 opacity-30" />
          <p>Nenhuma conversa encontrada</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 divide-y divide-slate-100">
          {filtered.map((c) => (
            <Link key={c.phone} href={`/conversations/${encodeURIComponent(c.phone)}`}>
              <div className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 cursor-pointer transition-all">
                <div className="w-10 h-10 bg-green-100 text-green-700 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0">
                  {c.phone_display.slice(-2)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-900">{c.phone_display}</p>
                    {c.needs_human && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                        Humano
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-500 truncate">{c.last_message}</p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock size={12} />
                      {timeAgo(c.last_timestamp)}
                    </p>
                    <p className="text-xs text-slate-400">{c.message_count} msgs</p>
                  </div>
                  <ChevronRight size={16} className="text-slate-300" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </Layout>
  )
}
