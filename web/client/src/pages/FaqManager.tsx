import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout'
import { Plus, RefreshCcw, Save, Trash2 } from 'lucide-react'

type FaqTopic = {
  _id: number
  id?: number
  titulo: string
  palavras_chave: string[]
  resumo: string
  ativo: boolean
  ordem: number
}

type AlertType = 'success' | 'error'

export default function FaqManager() {
  const [topics, setTopics] = useState<FaqTopic[]>([])
  const [selected, setSelected] = useState<FaqTopic | null>(null)
  const [originalSelected, setOriginalSelected] = useState<FaqTopic | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [search, setSearch] = useState('')
  const [alert, setAlert] = useState<{ type: AlertType; message: string } | null>(null)

  async function loadTopics(selectedId?: number) {
    setLoading(true)
    setAlert(null)

    try {
      const response = await fetch('/api/faq/topics', {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error(`Erro ao buscar FAQ: HTTP ${response.status}`)
      }

      const data: FaqTopic[] = await response.json()
      const normalized = data
        .map((topic) => ({
          ...topic,
          _id: Number(topic._id ?? topic.id),
          ordem: Number(topic.ordem ?? topic._id ?? topic.id),
          palavras_chave: Array.isArray(topic.palavras_chave) ? topic.palavras_chave : [],
          ativo: topic.ativo !== false
        }))
        .sort((a, b) => (a.ordem || a._id) - (b.ordem || b._id))

      setTopics(normalized)

      const nextSelected =
        normalized.find((topic) => topic._id === selectedId) ||
        (selected ? normalized.find((topic) => topic._id === selected._id) : null) ||
        normalized[0] ||
        null

      setSelected(nextSelected ? structuredClone(nextSelected) : null)
      setOriginalSelected(nextSelected ? structuredClone(nextSelected) : null)
      setEditing(false)
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.message || 'Erro ao carregar FAQ.'
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTopics()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const filteredTopics = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return topics
    }

    return topics.filter((topic) => {
      const keywordsText = (topic.palavras_chave || []).join(' ').toLowerCase()
      return (
        topic.titulo.toLowerCase().includes(query) ||
        topic.resumo.toLowerCase().includes(query) ||
        keywordsText.includes(query)
      )
    })
  }, [topics, search])

  function selectTopic(topic: FaqTopic) {
    if (editing) {
      const confirmChange = window.confirm('Existem alterações não salvas. Deseja descartar e trocar de tópico?')
      if (!confirmChange) return
    }

    setSelected(structuredClone(topic))
    setOriginalSelected(structuredClone(topic))
    setEditing(false)
    setAlert(null)
  }

  function startEditing() {
    if (!selected) return
    setOriginalSelected(structuredClone(selected))
    setEditing(true)
    setAlert(null)
  }

  function cancelEditing() {
    if (originalSelected) {
      setSelected(structuredClone(originalSelected))
    }

    setEditing(false)
    setAlert(null)
  }

  function updateSelected<K extends keyof FaqTopic>(field: K, value: FaqTopic[K]) {
    setSelected((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        [field]: value
      }
    })
  }

  function updateKeyword(index: number, value: string) {
    if (!selected) return

    const keywords = [...(selected.palavras_chave || [])]
    keywords[index] = value
    updateSelected('palavras_chave', keywords)
  }

  function addKeyword() {
    if (!selected) return

    updateSelected('palavras_chave', [
      ...(selected.palavras_chave || []),
      ''
    ])
  }

  function removeKeyword(index: number) {
    if (!selected) return

    const keywords = [...(selected.palavras_chave || [])]
    keywords.splice(index, 1)
    updateSelected('palavras_chave', keywords)
  }

  async function saveTopic() {
    if (!selected) return

    const payload: FaqTopic = {
      ...selected,
      titulo: selected.titulo.trim(),
      resumo: selected.resumo.trim(),
      palavras_chave: (selected.palavras_chave || [])
        .map((keyword) => keyword.trim())
        .filter(Boolean),
      ordem: Number(selected.ordem || selected._id),
      ativo: selected.ativo !== false
    }

    if (!payload.titulo) {
      setAlert({ type: 'error', message: 'Informe o título do tópico.' })
      return
    }

    if (!payload.resumo) {
      setAlert({ type: 'error', message: 'Informe o resumo/texto de resposta.' })
      return
    }

    setSaving(true)
    setAlert(null)

    try {
      const response = await fetch(`/api/faq/topics/${payload._id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`Erro ao salvar FAQ: HTTP ${response.status} - ${text}`)
      }

      setAlert({ type: 'success', message: 'Tópico salvo com sucesso.' })
      await loadTopics(payload._id)
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.message || 'Erro ao salvar tópico.'
      })
    } finally {
      setSaving(false)
    }
  }

  async function createTopic() {
    const titulo = window.prompt('Digite o título do novo tópico:')
    if (!titulo) return

    setSaving(true)
    setAlert(null)

    try {
      const payload = {
        titulo: titulo.trim(),
        palavras_chave: [],
        resumo: '',
        ativo: true,
        ordem: topics.length + 1
      }

      const response = await fetch('/api/faq/topics', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`Erro ao criar tópico: HTTP ${response.status} - ${text}`)
      }

      const data = await response.json()
      const topicId = Number(data.topic?._id ?? data.topic?.id)

      await loadTopics(topicId)
      setEditing(true)
      setAlert({ type: 'success', message: 'Novo tópico criado. Complete os dados e salve.' })
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.message || 'Erro ao criar tópico.'
      })
    } finally {
      setSaving(false)
    }
  }

  async function deactivateTopic() {
    if (!selected) return

    const confirmDelete = window.confirm(`Inativar o tópico "${selected.titulo}"?`)
    if (!confirmDelete) return

    setSaving(true)
    setAlert(null)

    try {
      const response = await fetch(`/api/faq/topics/${selected._id}`, {
        method: 'DELETE',
        credentials: 'include'
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`Erro ao inativar tópico: HTTP ${response.status} - ${text}`)
      }

      setAlert({ type: 'success', message: 'Tópico inativado com sucesso.' })
      setSelected(null)
      setOriginalSelected(null)
      setEditing(false)
      await loadTopics()
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.message || 'Erro ao inativar tópico.'
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout
      title="FAQ / Temas"
      subtitle="Gerencie palavras-chave e respostas automáticas do bot."
    >
      <div className="space-y-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex-1 max-w-xl">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por título, palavra-chave ou resumo..."
              className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>

          <div className="flex gap-2 justify-end">
            <button
              onClick={() => loadTopics(selected?._id)}
              disabled={loading || editing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCcw size={16} />
              Recarregar
            </button>

            <button
              onClick={createTopic}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
            >
              <Plus size={16} />
              Novo tópico
            </button>

            {!editing && selected && (
              <button
                onClick={startEditing}
                className="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
              >
                Editar
              </button>
            )}

            {editing && selected && (
              <>
                <button
                  onClick={cancelEditing}
                  disabled={saving}
                  className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Cancelar
                </button>

                <button
                  onClick={saveTopic}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                >
                  <Save size={16} />
                  {saving ? 'Salvando...' : 'Salvar'}
                </button>
              </>
            )}
          </div>
        </div>

        {alert && (
          <div
            className={`px-4 py-3 rounded-lg border ${
              alert.type === 'success'
                ? 'bg-green-50 text-green-700 border-green-200'
                : 'bg-red-50 text-red-700 border-red-200'
            }`}
          >
            {alert.message}
          </div>
        )}

        {loading && (
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            Carregando tópicos...
          </div>
        )}

        {!loading && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-slate-900">Tópicos</h2>
                <span className="text-xs text-slate-500">
                  {filteredTopics.length} de {topics.length}
                </span>
              </div>

              <div className="space-y-2 max-h-[680px] overflow-auto pr-1">
                {filteredTopics.map((topic) => (
                  <button
                    key={topic._id}
                    onClick={() => selectTopic(topic)}
                    className={`w-full text-left px-3 py-3 rounded-lg text-sm transition-all ${
                      selected?._id === topic._id
                        ? 'bg-primary-600 text-white'
                        : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium">
                        {topic.ordem || topic._id} - {topic.titulo}
                      </div>

                      {!topic.ativo && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-red-100 text-red-700">
                          Inativo
                        </span>
                      )}
                    </div>

                    <div className="text-xs opacity-80 mt-1">
                      {(topic.palavras_chave || []).length} palavras-chave
                    </div>
                  </button>
                ))}

                {filteredTopics.length === 0 && (
                  <div className="text-sm text-slate-500 py-4 text-center">
                    Nenhum tópico encontrado.
                  </div>
                )}
              </div>
            </div>

            <div className="xl:col-span-2 bg-white border border-slate-200 rounded-xl p-6">
              {!selected ? (
                <div className="text-slate-500">
                  Selecione um tópico para visualizar ou crie um novo tópico.
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 xl:grid-cols-[1fr_140px_120px] gap-4">
                    <Field label="Título">
                      {editing ? (
                        <input
                          value={selected.titulo}
                          onChange={(event) => updateSelected('titulo', event.target.value)}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                      ) : (
                        <ReadOnlyBox>{selected.titulo}</ReadOnlyBox>
                      )}
                    </Field>

                    <Field label="Ordem">
                      {editing ? (
                        <input
                          type="number"
                          value={selected.ordem}
                          onChange={(event) => updateSelected('ordem', Number(event.target.value || 0))}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                      ) : (
                        <ReadOnlyBox>{selected.ordem}</ReadOnlyBox>
                      )}
                    </Field>

                    <Field label="Ativo">
                      {editing ? (
                        <select
                          value={selected.ativo ? 'true' : 'false'}
                          onChange={(event) => updateSelected('ativo', event.target.value === 'true')}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        >
                          <option value="true">Sim</option>
                          <option value="false">Não</option>
                        </select>
                      ) : (
                        <ReadOnlyBox>{selected.ativo ? 'Sim' : 'Não'}</ReadOnlyBox>
                      )}
                    </Field>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-slate-900">Palavras-chave</h3>
                        <p className="text-sm text-slate-500">
                          Frases usadas para identificar este tema nas mensagens do usuário.
                        </p>
                      </div>

                      {editing && (
                        <button
                          onClick={addKeyword}
                          className="px-3 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700"
                        >
                          Adicionar palavra-chave
                        </button>
                      )}
                    </div>

                    <div className="space-y-2 max-h-[320px] overflow-auto pr-1">
                      {(selected.palavras_chave || []).map((keyword, index) => (
                        <div key={`keyword-${selected._id}-${index}`} className="flex gap-2">
                          {editing ? (
                            <>
                              <input
                                value={keyword}
                                onChange={(event) => updateKeyword(index, event.target.value)}
                                className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                              />

                              <button
                                onClick={() => removeKeyword(index)}
                                className="px-3 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100"
                              >
                                <Trash2 size={16} />
                              </button>
                            </>
                          ) : (
                            <ReadOnlyBox>{keyword}</ReadOnlyBox>
                          )}
                        </div>
                      ))}

                      {(selected.palavras_chave || []).length === 0 && (
                        <div className="text-sm text-slate-500 py-2">
                          Nenhuma palavra-chave cadastrada.
                        </div>
                      )}
                    </div>
                  </div>

                  <Field label="Resumo / texto de resposta">
                    {editing ? (
                      <textarea
                        value={selected.resumo}
                        onChange={(event) => updateSelected('resumo', event.target.value)}
                        rows={12}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                    ) : (
                      <div className="whitespace-pre-wrap px-3 py-2 border border-slate-200 rounded-lg bg-slate-100 text-slate-700 text-sm min-h-[220px]">
                        {selected.resumo || '-'}
                      </div>
                    )}
                  </Field>

                  {editing && (
                    <button
                      onClick={deactivateTopic}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-50"
                    >
                      <Trash2 size={16} />
                      Inativar tópico
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

type FieldProps = {
  label: string
  children: React.ReactNode
}

function Field({ label, children }: FieldProps) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </span>
      {children}
    </label>
  )
}

type ReadOnlyBoxProps = {
  children: React.ReactNode
}

function ReadOnlyBox({ children }: ReadOnlyBoxProps) {
  return (
    <div className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-100 text-slate-700 min-h-[38px]">
      {children || '-'}
    </div>
  )
}
