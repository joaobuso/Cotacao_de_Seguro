import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { Search, HelpCircle, ChevronDown, ChevronUp, Tag } from 'lucide-react'

interface FaqTopic {
  id: string
  titulo: string
  resumo: string
  palavras_chave: string[]
}

export default function FaqManager() {
  const [topics, setTopics] = useState<FaqTopic[]>([])
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/faq', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : []))
      .then((d: FaqTopic[]) => setTopics(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = topics.filter(
    (t) =>
      t.titulo.toLowerCase().includes(search.toLowerCase()) ||
      t.resumo.toLowerCase().includes(search.toLowerCase()) ||
      t.palavras_chave.some((p) => p.toLowerCase().includes(search.toLowerCase())),
  )

  return (
    <Layout title="FAQ / Temas" subtitle="Base de conhecimento do bot - 21 temas configurados">
      <div className="flex items-center mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar tema ou palavra-chave..."
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
          <HelpCircle size={48} className="mx-auto mb-4 opacity-30" />
          <p>Nenhum tema encontrado</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((t) => {
            const isOpen = expanded === t.id
            return (
              <div key={t.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <button
                  onClick={() => setExpanded(isOpen ? null : t.id)}
                  className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-slate-50 transition-all"
                >
                  <div className="w-10 h-10 bg-primary-100 text-primary-700 rounded-lg flex items-center justify-center flex-shrink-0">
                    <HelpCircle size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900">{t.titulo}</p>
                    {!isOpen && <p className="text-sm text-slate-500 truncate">{t.resumo}</p>}
                  </div>
                  {isOpen ? <ChevronUp size={20} className="text-slate-400" /> : <ChevronDown size={20} className="text-slate-400" />}
                </button>

                {isOpen && (
                  <div className="px-6 pb-5 border-t border-slate-100 pt-4">
                    <p className="text-sm text-slate-700 leading-relaxed mb-4">{t.resumo}</p>
                    <div>
                      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                        <Tag size={12} /> Palavras-chave
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {t.palavras_chave.map((kw) => (
                          <span key={kw} className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-full text-xs">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}
