import React, { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import { HelpCircle, ChevronDown, ChevronUp, Search, Tag } from 'lucide-react'

interface FaqTopic {
  id: number
  titulo: string
  resumo: string
  palavras_chave: string[]
}

export default function FaqManager() {
  const [topics, setTopics] = useState<FaqTopic[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    fetch('/api/faq', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setTopics(data))
      .catch(err => console.error('Erro:', err))
      .finally(() => setLoading(false))
  }, [])

  const filtered = topics.filter(t =>
    t.titulo.toLowerCase().includes(search.toLowerCase()) ||
    t.resumo.toLowerCase().includes(search.toLowerCase()) ||
    t.palavras_chave.some(k => k.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <Layout title="FAQ / Temas" subtitle="21 temas de perguntas frequentes usados pelo bot">
      {/* Search */}
      <div className="relative max-w-md mb-6">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar temas..."
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((topic) => (
            <div key={topic.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <button
                onClick={() => setExpandedId(expandedId === topic.id ? null : topic.id)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-all text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center text-sm font-bold text-primary-600">
                    {topic.id}
                  </div>
                  <h3 className="font-medium text-slate-900">{topic.titulo}</h3>
                </div>
                {expandedId === topic.id ? (
                  <ChevronUp size={20} className="text-slate-400" />
                ) : (
                  <ChevronDown size={20} className="text-slate-400" />
                )}
              </button>

              {expandedId === topic.id && (
                <div className="px-6 pb-6 border-t border-slate-100">
                  <div className="mt-4 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed bg-slate-50 rounded-lg p-4">
                    {topic.resumo}
                  </div>
                  <div className="mt-4">
                    <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                      <Tag size={12} /> Palavras-chave
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {topic.palavras_chave.map((kw, i) => (
                        <span key={i} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
              <HelpCircle size={48} className="mx-auto text-slate-300 mb-4" />
              <h3 className="text-lg font-medium text-slate-600">Nenhum tema encontrado</h3>
            </div>
          )}
        </div>
      )}
    </Layout>
  )
}
