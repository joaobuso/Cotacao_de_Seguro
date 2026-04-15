import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { Users, Bot, UserCheck, AlertTriangle, FileCheck, Clock } from 'lucide-react'

interface Stats {
  total_clients: number
  bot_handled: number
  human_handled: number
  human_needed: number
  quotations_completed: number
  quotations_by_bot: number
  quotations_by_human: number
  quotations_failed: number
  today_conversations: number
}

const empty: Stats = {
  total_clients: 0, bot_handled: 0, human_handled: 0, human_needed: 0,
  quotations_completed: 0, quotations_by_bot: 0, quotations_by_human: 0,
  quotations_failed: 0, today_conversations: 0,
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>(empty)
  const [loading, setLoading] = useState(true)

  const load = () => {
    fetch('/api/stats', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : empty))
      .then((d: Stats) => setStats(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [])

  const cards = [
    { label: 'Total Clientes', value: stats.total_clients, icon: Users, color: 'bg-blue-500' },
    { label: 'Atendidos pelo Bot', value: stats.bot_handled, icon: Bot, color: 'bg-green-500' },
    { label: 'Atendidos por Humano', value: stats.human_handled, icon: UserCheck, color: 'bg-purple-500' },
    { label: 'Aguardando Humano', value: stats.human_needed, icon: AlertTriangle, color: 'bg-amber-500' },
    { label: 'Cotações Concluídas', value: stats.quotations_completed, icon: FileCheck, color: 'bg-emerald-500' },
    { label: 'Conversas Hoje', value: stats.today_conversations, icon: Clock, color: 'bg-indigo-500' },
  ]

  const pct = (a: number, b: number) => (a + b > 0 ? (a / (a + b)) * 100 : 0)

  return (
    <Layout title="Dashboard" subtitle="Visão geral do sistema de cotações">
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {cards.map((c) => {
              const Icon = c.icon
              return (
                <div key={c.label} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center gap-4">
                  <div className={`${c.color} w-12 h-12 rounded-lg flex items-center justify-center text-white`}><Icon size={24} /></div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">{c.value}</p>
                    <p className="text-sm text-slate-500">{c.label}</p>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Bot vs Humano</h3>
              <div className="space-y-4">
                {[
                  { label: 'Bot', val: stats.quotations_by_bot, cls: 'bg-green-500' },
                  { label: 'Humano', val: stats.quotations_by_human, cls: 'bg-purple-500' },
                ].map((b) => (
                  <div key={b.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-600">{b.label}</span>
                      <span className="font-medium">{b.val}</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-3">
                      <div className={`${b.cls} h-3 rounded-full transition-all`} style={{ width: `${pct(b.val, b.label === 'Bot' ? stats.quotations_by_human : stats.quotations_by_bot)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Resumo de Cotações</h3>
              <div className="space-y-3">
                {[
                  { label: 'Concluídas', val: stats.quotations_completed, cls: 'bg-green-100 text-green-700' },
                  { label: 'Falhas', val: stats.quotations_failed, cls: 'bg-red-100 text-red-700' },
                  { label: 'Por Bot', val: stats.quotations_by_bot, cls: 'bg-blue-100 text-blue-700' },
                  { label: 'Por Humano', val: stats.quotations_by_human, cls: 'bg-purple-100 text-purple-700' },
                ].map((r) => (
                  <div key={r.label} className="flex justify-between items-center">
                    <span className="text-slate-600">{r.label}</span>
                    <span className={`px-3 py-1 ${r.cls} rounded-full text-sm font-medium`}>{r.val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </Layout>
  )
}
