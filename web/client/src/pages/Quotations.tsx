import React, { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import { FileText, RefreshCw, CheckCircle, XCircle, Bot, UserCheck, Search } from 'lucide-react'

interface Quotation {
  phone: string
  phone_display: string
  status: string
  completed_by: string
  agent_email: string
  created_at: string | null
  client_data: Record<string, string>
}

export default function Quotations() {
  const [quotations, setQuotations] = useState<Quotation[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const fetchQuotations = async () => {
    try {
      const res = await fetch('/api/quotations', { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setQuotations(data)
      }
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQuotations()
  }, [])

  const filtered = quotations.filter(q =>
    q.phone_display.toLowerCase().includes(search.toLowerCase()) ||
    q.phone.includes(search) ||
    q.status.toLowerCase().includes(search.toLowerCase())
  )

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
            <CheckCircle size={12} /> Concluída
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
            <XCircle size={12} /> Falha
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
            Processando
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-full">
            {status}
          </span>
        )
    }
  }

  const getCompletedByBadge = (by: string) => {
    if (by === 'bot') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-600">
          <Bot size={14} /> Bot
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs text-orange-600">
        <UserCheck size={14} /> Humano
      </span>
    )
  }

  const formatDate = (ts: string | null) => {
    if (!ts) return '-'
    try {
      return new Date(ts).toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      })
    } catch {
      return '-'
    }
  }

  return (
    <Layout title="Cotações" subtitle="Histórico de cotações realizadas">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar cotações..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>
        <button
          onClick={() => { setLoading(true); fetchQuotations() }}
          className="flex items-center gap-2 px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all text-slate-600 ml-4"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
          <FileText size={48} className="mx-auto text-slate-300 mb-4" />
          <h3 className="text-lg font-medium text-slate-600">Nenhuma cotação encontrada</h3>
          <p className="text-sm text-slate-400 mt-1">As cotações aparecerão aqui quando forem realizadas.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Cliente</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Realizada por</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Data</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Dados</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((q, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-slate-900">{q.phone_display}</p>
                      <p className="text-xs text-slate-400">{q.phone}</p>
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(q.status)}</td>
                    <td className="px-6 py-4">
                      {getCompletedByBadge(q.completed_by)}
                      {q.agent_email && (
                        <p className="text-xs text-slate-400 mt-1">{q.agent_email}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{formatDate(q.created_at)}</td>
                    <td className="px-6 py-4">
                      {q.client_data && Object.keys(q.client_data).length > 0 ? (
                        <div className="text-xs text-slate-500 space-y-0.5">
                          {Object.entries(q.client_data).slice(0, 3).map(([key, value]) => (
                            <p key={key}>
                              <span className="font-medium">{key.replace(/_/g, ' ')}:</span> {value}
                            </p>
                          ))}
                          {Object.keys(q.client_data).length > 3 && (
                            <p className="text-slate-400">+{Object.keys(q.client_data).length - 3} campos</p>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Layout>
  )
}
