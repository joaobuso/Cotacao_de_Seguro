import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { Search, FileText } from 'lucide-react'

interface Quotation {
  phone: string
  phone_display: string
  status: string
  completed_by: string
  agent_email: string
  created_at: string | null
  client_data: Record<string, string>
}

function fmtDate(iso: string | null): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return '-'
  }
}

function statusBadge(s: string) {
  if (s === 'completed') return { label: 'Concluída', cls: 'bg-green-100 text-green-700' }
  if (s === 'failed') return { label: 'Falha', cls: 'bg-red-100 text-red-700' }
  return { label: s || 'Pendente', cls: 'bg-slate-100 text-slate-700' }
}

export default function Quotations() {
  const [list, setList] = useState<Quotation[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/quotations', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : []))
      .then((d: Quotation[]) => setList(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = list.filter(
    (q) =>
      q.phone.includes(search) ||
      q.phone_display.toLowerCase().includes(search.toLowerCase()) ||
      (q.agent_email || '').toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <Layout title="Cotações" subtitle="Histórico de cotações realizadas">
      <div className="flex items-center mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por telefone ou agente..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          <FileText size={48} className="mx-auto mb-4 opacity-30" />
          <p>Nenhuma cotação encontrada</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-6 py-3 font-medium text-slate-600">Telefone</th>
                <th className="text-left px-6 py-3 font-medium text-slate-600">Status</th>
                <th className="text-left px-6 py-3 font-medium text-slate-600">Concluída por</th>
                <th className="text-left px-6 py-3 font-medium text-slate-600">Agente</th>
                <th className="text-left px-6 py-3 font-medium text-slate-600">Data</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((q, i) => {
                const badge = statusBadge(q.status)
                return (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-900">{q.phone_display}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${badge.cls}`}>{badge.label}</span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 capitalize">{q.completed_by || '-'}</td>
                    <td className="px-6 py-4 text-slate-600">{q.agent_email || '-'}</td>
                    <td className="px-6 py-4 text-slate-500">{fmtDate(q.created_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  )
}
