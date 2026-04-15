import React, { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import {
  Users,
  Bot,
  UserCheck,
  AlertTriangle,
  FileCheck,
  TrendingUp,
  MessageSquare,
  RefreshCw
} from 'lucide-react'

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

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats', { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Erro ao buscar stats:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const cards = stats ? [
    { label: 'Total de Clientes', value: stats.total_clients, icon: Users, color: 'bg-blue-500', textColor: 'text-blue-600', bgLight: 'bg-blue-50' },
    { label: 'Atendidos pelo Bot', value: stats.bot_handled, icon: Bot, color: 'bg-green-500', textColor: 'text-green-600', bgLight: 'bg-green-50' },
    { label: 'Atendidos por Humano', value: stats.human_handled, icon: UserCheck, color: 'bg-orange-500', textColor: 'text-orange-600', bgLight: 'bg-orange-50' },
    { label: 'Precisam de Humano', value: stats.human_needed, icon: AlertTriangle, color: 'bg-red-500', textColor: 'text-red-600', bgLight: 'bg-red-50' },
    { label: 'Cotações Concluídas', value: stats.quotations_completed, icon: FileCheck, color: 'bg-emerald-500', textColor: 'text-emerald-600', bgLight: 'bg-emerald-50' },
    { label: 'Cotações pelo Bot', value: stats.quotations_by_bot, icon: TrendingUp, color: 'bg-cyan-500', textColor: 'text-cyan-600', bgLight: 'bg-cyan-50' },
    { label: 'Cotações por Humano', value: stats.quotations_by_human, icon: UserCheck, color: 'bg-purple-500', textColor: 'text-purple-600', bgLight: 'bg-purple-50' },
    { label: 'Conversas Hoje', value: stats.today_conversations, icon: MessageSquare, color: 'bg-indigo-500', textColor: 'text-indigo-600', bgLight: 'bg-indigo-50' },
  ] : []

  return (
    <Layout title="Dashboard" subtitle="Visão geral do sistema de cotações">
      <div className="flex items-center justify-between mb-6">
        <div></div>
        <button
          onClick={() => { setLoading(true); fetchStats() }}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all text-slate-600"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {loading && !stats ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {cards.map((card, i) => {
              const Icon = card.icon
              return (
                <div key={i} className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-all">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 ${card.bgLight} rounded-lg flex items-center justify-center`}>
                      <Icon size={24} className={card.textColor} />
                    </div>
                  </div>
                  <p className="text-3xl font-bold text-slate-900">{card.value}</p>
                  <p className="text-sm text-slate-500 mt-1">{card.label}</p>
                </div>
              )
            })}
          </div>

          {/* Info Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Desempenho Bot vs Humano</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Atendimentos pelo Bot</span>
                    <span className="font-medium text-green-600">{stats?.bot_handled || 0}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3">
                    <div
                      className="bg-green-500 h-3 rounded-full transition-all"
                      style={{
                        width: `${stats && (stats.bot_handled + stats.human_handled) > 0
                          ? (stats.bot_handled / (stats.bot_handled + stats.human_handled)) * 100
                          : 0}%`
                      }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Atendimentos por Humano</span>
                    <span className="font-medium text-orange-600">{stats?.human_handled || 0}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3">
                    <div
                      className="bg-orange-500 h-3 rounded-full transition-all"
                      style={{
                        width: `${stats && (stats.bot_handled + stats.human_handled) > 0
                          ? (stats.human_handled / (stats.bot_handled + stats.human_handled)) * 100
                          : 0}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Resumo de Cotações</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-600">Concluídas</span>
                  <span className="font-semibold text-emerald-600">{stats?.quotations_completed || 0}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-600">Pelo Bot</span>
                  <span className="font-semibold text-cyan-600">{stats?.quotations_by_bot || 0}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-600">Por Humano</span>
                  <span className="font-semibold text-purple-600">{stats?.quotations_by_human || 0}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-slate-600">Falhas</span>
                  <span className="font-semibold text-red-600">{stats?.quotations_failed || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </Layout>
  )
}
