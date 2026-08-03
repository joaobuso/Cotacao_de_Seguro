import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { RefreshCcw, Save } from 'lucide-react'

type Rules = Record<string, any>
type Tab =
  | 'geral'
  | 'produtos'
  | 'limites'
  | 'franquias'
  | 'idades'
  | 'sexo'
  | 'utilizacoes'
  | 'racas'
  | 'asininos_muares'

export default function SwissReRules() {
  const [rules, setRules] = useState<Rules | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('geral')
  const [editing, setEditing] = useState(false)
  const [originalRules, setOriginalRules] = useState<Rules | null>(null)

  async function loadRules() {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/swissre/rules', {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error(`Erro ao buscar regras: HTTP ${response.status}`)
      }

      const data = await response.json()
      setRules(data)
      setOriginalRules(structuredClone(data))
      setEditing(false)
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar regras')
    } finally {
      setLoading(false)
    }
  }

  async function saveRules() {
    if (!rules) return

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/swissre/rules', {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(rules)
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`Erro ao salvar regras: HTTP ${response.status} - ${text}`)
      }

      setSuccess('Regras salvas com sucesso.')
      setOriginalRules(structuredClone(rules))
      setEditing(false)
    } catch (err: any) {
      setError(err.message || 'Erro ao salvar regras')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    loadRules()
  }, [])

  function startEditing() {
    if (!rules) return
    setOriginalRules(structuredClone(rules))
    setEditing(true)
    setSuccess(null)
    setError(null)
  }

  function cancelEditing() {
    if (originalRules) {
      setRules(structuredClone(originalRules))
    }

    setEditing(false)
    setSuccess(null)
    setError(null)
  }

  function updateGeneralField(field: string, value: any) {
    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        general: {
          ...prev.general,
          [field]: value
        }
      }
    })
  }

  function updateLimiteUtilizacao(codigo: string, field: string, value: any) {
    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        limitesPorUtilizacao: {
          ...prev.limitesPorUtilizacao,
          [codigo]: {
            ...prev.limitesPorUtilizacao?.[codigo],
            [field]: value
          }
        }
      }
    })
  }

  function updateFranquia(chave: string, field: string, value: any) {
    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        franquiasPorUtilizacaoCobertura: {
          ...prev.franquiasPorUtilizacaoCobertura,
          [chave]: {
            ...prev.franquiasPorUtilizacaoCobertura?.[chave],
            [field]: value
          }
        }
      }
    })
  }

  function updateIdade(codigo: string, field: string, value: any) {
    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        idadePorUtilizacao: {
          ...prev.idadePorUtilizacao,
          [codigo]: {
            ...prev.idadePorUtilizacao?.[codigo],
            [field]: value
          }
        }
      }
    })
  }

  function updateCoverage(productId: string, planoId: string, index: number, field: string, value: any) {
    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      newRules.products[productId].planos[planoId].coverages[index][field] = value
      return newRules
    })
  }

  function updateNestedField(path: string[], value: any) {
    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      let current = newRules

      for (let i = 0; i < path.length - 1; i++) {
        if (!current[path[i]]) {
          current[path[i]] = {}
        }
        current = current[path[i]]
      }

      current[path[path.length - 1]] = value
      return newRules
    })
  }

  function updateMapValue(section: string, key: string, value: string) {
    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        [section]: {
          ...prev[section],
          [key]: value
        }
      }
    })
  }

  function updateTermsValue(section: string, key: string, value: string) {
    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        [section]: {
          ...prev[section],
          termos: {
            ...prev[section]?.termos,
            [key]: value
          }
        }
      }
    })
  }

  function addMapItem(section: string) {
    const key = window.prompt('Digite o termo/chave:')
    if (!key) return

    const value = window.prompt('Digite o código/valor:')
    if (!value) return

    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        [section]: {
          ...prev[section],
          [key]: value
        }
      }
    })
  }

  function removeMapItem(section: string, key: string) {
    if (!window.confirm(`Remover "${key}"?`)) return

    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      delete newRules[section][key]
      return newRules
    })
  }

  function addTermsItem(section: string) {
    const key = window.prompt('Digite o termo:')
    if (!key) return

    const value = window.prompt('Digite o código:')
    if (!value) return

    setRules((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        [section]: {
          ...prev[section],
          termos: {
            ...prev[section]?.termos,
            [key]: value
          }
        }
      }
    })
  }

  function removeTermsItem(section: string, key: string) {
    if (!window.confirm(`Remover "${key}"?`)) return

    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      delete newRules[section].termos[key]
      return newRules
    })
  }

  function addListItem(path: string[]) {
    const value = window.prompt('Digite o termo:')
    if (!value) return

    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      let current = newRules

      for (const key of path) {
        current = current[key]
      }

      if (!Array.isArray(current)) return prev
      current.push(value)
      return newRules
    })
  }

  function updateListItem(path: string[], index: number, value: string) {
    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      let current = newRules

      for (const key of path) {
        current = current[key]
      }

      if (!Array.isArray(current)) return prev
      current[index] = value
      return newRules
    })
  }

  function removeListItem(path: string[], index: number) {
    if (!window.confirm('Remover este termo?')) return

    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      let current = newRules

      for (const key of path) {
        current = current[key]
      }

      if (!Array.isArray(current)) return prev
      current.splice(index, 1)
      return newRules
    })
  }

  function renderTabContent() {
    if (!rules) return null

    if (tab === 'geral') {
      return (
        <Section title="Configurações Gerais" description="Dados usados em todas as cotações.">
          <Grid>
            <Input label="CPF/CNPJ padrão" value={rules.general?.cpf || ''} editing={editing} onChange={(v) => updateGeneralField('cpf', v)} />
            <Input label="Broker ID" value={rules.general?.brokerId || ''} editing={editing} onChange={(v) => updateGeneralField('brokerId', v)} />
            <Input label="Product Version ID" value={rules.general?.productVersionId || ''} editing={editing} onChange={(v) => updateGeneralField('productVersionId', v)} />
            <Input label="Código Afinidade" value={rules.general?.codAfinidade || ''} editing={editing} onChange={(v) => updateGeneralField('codAfinidade', v)} />
            <Input label="Plano Padrão" value={rules.general?.codPlanoPadrao || ''} editing={editing} onChange={(v) => updateGeneralField('codPlanoPadrao', v)} />
            <Input label="Plano Simplificado" value={rules.general?.codPlanoSimplificado || ''} editing={editing} onChange={(v) => updateGeneralField('codPlanoSimplificado', v)} />
          </Grid>
        </Section>
      )
    }

    if (tab === 'produtos') {
      return (
        <div className="space-y-6">
          {Object.entries(rules.products || {}).map(([productId, product]: any) => (
            <Section key={productId} title={`${productId} - ${product.descricao}`} description="Coberturas configuradas por plano.">
              {Object.entries(product.planos || {}).map(([planoId, plano]: any) => (
                <div key={planoId} className="mb-6 last:mb-0">
                  <h3 className="font-semibold text-slate-900 mb-3">
                    Plano {planoId} - {plano.descricao}
                  </h3>

                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-200 text-left text-slate-500">
                          <th className="py-2 pr-4">ID</th>
                          <th className="py-2 pr-4">Descrição</th>
                          <th className="py-2 pr-4">Tipo</th>
                          <th className="py-2 pr-4">Valor Fixo</th>
                          <th className="py-2 pr-4">Valor Máximo</th>
                          <th className="py-2 pr-4">Franquia %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(plano.coverages || []).map((cov: any, index: number) => (
                          <tr key={`${cov.id}-${index}`} className="border-b border-slate-100">
                            <td className="py-2 pr-4"><SmallInput value={cov.id || ''} editing={editing} onChange={(v) => updateCoverage(productId, planoId, index, 'id', v)} /></td>
                            <td className="py-2 pr-4 min-w-[260px]"><SmallInput value={cov.descricao || ''} editing={editing} onChange={(v) => updateCoverage(productId, planoId, index, 'descricao', v)} /></td>
                            <td className="py-2 pr-4"><SmallInput value={cov.tipo || ''} editing={editing} onChange={(v) => updateCoverage(productId, planoId, index, 'tipo', v)} /></td>
                            <td className="py-2 pr-4"><SmallInput value={cov.valorFixo ?? ''} editing={editing} onChange={(v) => updateCoverage(productId, planoId, index, 'valorFixo', toNumberOrEmpty(v))} /></td>
                            <td className="py-2 pr-4"><SmallInput value={cov.valorMaximo ?? ''} editing={editing} onChange={(v) => updateCoverage(productId, planoId, index, 'valorMaximo', toNumberOrEmpty(v))} /></td>
                            <td className="py-2 pr-4"><SmallInput value={cov.pctFranchise ?? 0} editing={editing} onChange={(v) => updateCoverage(productId, planoId, index, 'pctFranchise', Number(v || 0))} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </Section>
          ))}
        </div>
      )
    }

    if (tab === 'limites') {
      return (
        <Section title="Limites por Utilização" description="Regras que limitam o valor segurado conforme a utilização do animal. Exemplo: Lazer limitado a R$ 15.000 na cobertura básica.">
          <div className="space-y-4">
            {Object.entries(rules.limitesPorUtilizacao || {}).map(([codigo, regra]: any) => (
              <div key={codigo} className="grid grid-cols-1 md:grid-cols-4 gap-4 border border-slate-200 rounded-lg p-4">
                <Input label="Código Utilização" value={codigo} disabled />
                <Input label="Descrição" value={regra.descricao || ''} editing={editing} onChange={(v) => updateLimiteUtilizacao(codigo, 'descricao', v)} />
                <Input label="Valor Máximo Básica" type="number" value={regra.valorMaximoBasica || ''} editing={editing} onChange={(v) => updateLimiteUtilizacao(codigo, 'valorMaximoBasica', Number(v || 0))} />
                <Input label="Aplicar em" value={(regra.aplicarEm || []).join(', ')} editing={editing} onChange={(v) => updateLimiteUtilizacao(codigo, 'aplicarEm', v.split(',').map((x) => x.trim()))} />
              </div>
            ))}
          </div>
        </Section>
      )
    }

    if (tab === 'franquias') {
      return (
        <Section title="Franquias por Utilização e Cobertura" description="Define percentual de franquia quando a SwissRe exigir valor específico por utilização/cobertura.">
          <div className="space-y-4">
            {Object.entries(rules.franquiasPorUtilizacaoCobertura || {}).map(([chave, regra]: any) => {
              const [codigoUtilizacao, coverageId] = chave.split('|')

              return (
                <div key={chave} className="grid grid-cols-1 md:grid-cols-4 gap-4 border border-slate-200 rounded-lg p-4">
                  <Input label="Utilização" value={codigoUtilizacao} disabled />
                  <Input label="Cobertura" value={coverageId} disabled />
                  <Input label="Descrição" value={regra.descricao || ''} editing={editing} onChange={(v) => updateFranquia(chave, 'descricao', v)} />
                  <Input label="Franquia %" type="number" value={regra.pctFranchise ?? 0} editing={editing} onChange={(v) => updateFranquia(chave, 'pctFranchise', Number(v || 0))} />
                </div>
              )
            })}
          </div>
        </Section>
      )
    }

    if (tab === 'idades') {
      return (
        <Section title="Idade por Utilização" description="Regras de idade mínima e máxima conforme a utilização informada.">
          <div className="space-y-4">
            {Object.entries(rules.idadePorUtilizacao || {}).map(([codigo, regra]: any) => (
              <div key={codigo} className="grid grid-cols-1 md:grid-cols-4 gap-4 border border-slate-200 rounded-lg p-4">
                <Input label="Código" value={codigo} disabled />
                <Input label="Descrição" value={regra.descricao || ''} editing={editing} onChange={(v) => updateIdade(codigo, 'descricao', v)} />
                <Input label="Idade mínima meses" type="number" value={regra.minMeses ?? 4} editing={editing} onChange={(v) => updateIdade(codigo, 'minMeses', Number(v || 0))} />
                <Input label="Idade máxima meses" type="number" value={regra.maxMeses ?? ''} editing={editing} onChange={(v) => updateIdade(codigo, 'maxMeses', Number(v || 0))} />
              </div>
            ))}
          </div>
        </Section>
      )
    }

    if (tab === 'sexo') {
      return (
        <Section title="Mapeamento de Sexo" description="Define os códigos enviados para a SwissRe conforme o sexo informado pelo cliente.">
          <div className="space-y-6">
            <Grid>
              <Input label="Código fallback" value={rules.sexoAnimal?.fallbackCodigo || ''} editing={editing} onChange={(v) => updateNestedField(['sexoAnimal', 'fallbackCodigo'], v)} />
            </Grid>

            <div>
              <h3 className="font-semibold text-slate-900 mb-3">
                Descrições dos códigos
              </h3>

              <div className="border border-slate-200 rounded-lg overflow-hidden">
                {Object.entries(rules.sexoAnimal?.descricoes || {})
                  .sort(([codigoA], [codigoB]) => Number(codigoA) - Number(codigoB))
                  .map(([codigo, descricao]: any) => (
                    <div
                      key={codigo}
                      className="flex items-center justify-between gap-4 px-4 py-3 border-b border-slate-100 last:border-b-0 bg-white"
                    >
                      {!editing ? (
                        <>
                          <span className="text-sm font-medium text-slate-700">
                            {descricao}:
                          </span>

                          <span className="text-sm font-semibold text-slate-900">
                            {codigo}
                          </span>
                        </>
                      ) : (
                        <>
                          <input
                            value={String(descricao ?? '')}
                            onChange={(e) =>
                              updateNestedField(
                                ['sexoAnimal', 'descricoes', codigo],
                                e.target.value
                              )
                            }
                            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                          />

                          <div className="w-28 px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-100 text-slate-700 text-center">
                            Código {codigo}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
              </div>
            </div>

            <EditableMap
              title="Termos reconhecidos"
              description="Palavras que o bot reconhece e converte para código de sexo."
              data={rules.sexoAnimal?.termos || {}}
              editing={editing}
              onChange={(key, value) => updateNestedField(['sexoAnimal', 'termos', key], value)}
              onAdd={() => addTermsItem('sexoAnimal')}
              onRemove={(key) => removeTermsItem('sexoAnimal', key)}
            />
          </div>
        </Section>
      )
    }

    if (tab === 'utilizacoes') {
      return (
        <Section title="Mapeamento de Utilizações - Equinos" description="Palavras digitadas pelo cliente e o código de utilização enviado para a SwissRe.">
          <EditableMap
            title="Utilizações"
            description='Exemplo: "tambor" → "52", "freio de ouro" → "52", "exposição" → "45".'
            data={rules.utilizacoesEquinos || {}}
            editing={editing}
            onChange={(key, value) => updateMapValue('utilizacoesEquinos', key, value)}
            onAdd={() => addMapItem('utilizacoesEquinos')}
            onRemove={(key) => removeMapItem('utilizacoesEquinos', key)}
          />
        </Section>
      )
    }

    if (tab === 'racas') {
      return (
        <Section title="Mapeamento de Raças - Equinos" description="Raças digitadas pelo cliente e o código de enquadramento enviado para a SwissRe.">
          <div className="space-y-6">
            <Grid>
              <Input label="Código fallback" value={rules.racasEquinos?.fallbackCodigo || ''} editing={editing} onChange={(v) => updateNestedField(['racasEquinos', 'fallbackCodigo'], v)} />
            </Grid>

            <EditableMap
              title="Raças"
              description='Exemplo: "quarto de milha" → "1022", "crioulo" → "1007", "srd" → "1025".'
              data={rules.racasEquinos?.termos || {}}
              editing={editing}
              onChange={(key, value) => updateTermsValue('racasEquinos', key, value)}
              onAdd={() => addTermsItem('racasEquinos')}
              onRemove={(key) => removeTermsItem('racasEquinos', key)}
            />
          </div>
        </Section>
      )
    }

    if (tab === 'asininos_muares') {
      return (
        <Section title="Mapeamentos - Asininos e Muares" description="Regras usadas para identificar produto, grupo, utilização e raça para o productId 64017.">
          <div className="space-y-6">
            <EditableList
              title="Termos que identificam produto 64017"
              description='Exemplo: "mula", "mulo", "burro", "jumento", "jegue".'
              data={Array.isArray(rules.termosProdutoMula) ? rules.termosProdutoMula : []}
              editing={editing}
              onChange={(index, value) => updateListItem(['termosProdutoMula'], index, value)}
              onAdd={() => addListItem(['termosProdutoMula'])}
              onRemove={(index) => removeListItem(['termosProdutoMula'], index)}
            />

            <EditableList
              title="Grupo Muares"
              description="Termos que classificam o animal como muar."
              data={Array.isArray(rules.gruposAsininosMuares?.muares) ? rules.gruposAsininosMuares.muares : []}
              editing={editing}
              onChange={(index, value) => updateListItem(['gruposAsininosMuares', 'muares'], index, value)}
              onAdd={() => addListItem(['gruposAsininosMuares', 'muares'])}
              onRemove={(index) => removeListItem(['gruposAsininosMuares', 'muares'], index)}
            />

            <EditableList
              title="Grupo Asininos"
              description="Termos que classificam o animal como asinino."
              data={Array.isArray(rules.gruposAsininosMuares?.asininos) ? rules.gruposAsininosMuares.asininos : []}
              editing={editing}
              onChange={(index, value) => updateListItem(['gruposAsininosMuares', 'asininos'], index, value)}
              onAdd={() => addListItem(['gruposAsininosMuares', 'asininos'])}
              onRemove={(index) => removeListItem(['gruposAsininosMuares', 'asininos'], index)}
            />

            <Grid>
              <Input
                label="Grupo fallback"
                value={rules.gruposAsininosMuares?.fallbackGrupo || ''}
                editing={editing}
                onChange={(v) => updateNestedField(['gruposAsininosMuares', 'fallbackGrupo'], v)}
              />
            </Grid>

            <EditableMap
              title="Utilizações 64017 - Asininos"
              description='Exemplo: "lazer" → "47", "exposicao" → "45".'
              data={rules.utilizacoes64017?.asininos || {}}
              editing={editing}
              onChange={(key, value) => updateNestedField(['utilizacoes64017', 'asininos', key], value)}
              onAdd={() => addNestedMapItem(['utilizacoes64017', 'asininos'])}
              onRemove={(key) => removeNestedMapItem(['utilizacoes64017', 'asininos'], key)}
            />

            <EditableMap
              title="Utilizações 64017 - Muares"
              description='Exemplo: "lazer" → "61", "exposicao" → "60".'
              data={rules.utilizacoes64017?.muares || {}}
              editing={editing}
              onChange={(key, value) => updateNestedField(['utilizacoes64017', 'muares', key], value)}
              onAdd={() => addNestedMapItem(['utilizacoes64017', 'muares'])}
              onRemove={(key) => removeNestedMapItem(['utilizacoes64017', 'muares'], key)}
            />

            <EditableMap
              title="Raças 64017"
              description='Exemplo: "catala" → "00001", "pega" → "00002", "srd" → "00003".'
              data={rules.racas64017?.termos || rules.racas64017 || {}}
              editing={editing}
              onChange={(key, value) => {
                if (rules.racas64017?.termos) {
                  updateTermsValue('racas64017', key, value)
                } else {
                  updateMapValue('racas64017', key, value)
                }
              }}
              onAdd={() => {
                if (rules.racas64017?.termos) {
                  addTermsItem('racas64017')
                } else {
                  addMapItem('racas64017')
                }
              }}
              onRemove={(key) => {
                if (rules.racas64017?.termos) {
                  removeTermsItem('racas64017', key)
                } else {
                  removeMapItem('racas64017', key)
                }
              }}
            />
          </div>
        </Section>
      )
    }

    return null
  }

  function addNestedMapItem(path: string[]) {
    const key = window.prompt('Digite o termo/chave:')
    if (!key) return

    const value = window.prompt('Digite o código/valor:')
    if (!value) return

    updateNestedField([...path, key], value)
  }

  function removeNestedMapItem(path: string[], key: string) {
    if (!window.confirm(`Remover "${key}"?`)) return

    setRules((prev) => {
      if (!prev) return prev
      const newRules = structuredClone(prev)
      let current = newRules

      for (const pathKey of path) {
        current = current[pathKey]
      }

      delete current[key]
      return newRules
    })
  }

  return (
    <Layout
      title="Regras SwissRe"
      subtitle="Configure produtos, coberturas, limites, franquias e regras de idade."
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex gap-2 flex-wrap">
            <TabButton active={tab === 'geral'} onClick={() => setTab('geral')}>Geral</TabButton>
            <TabButton active={tab === 'produtos'} onClick={() => setTab('produtos')}>Produtos e Coberturas</TabButton>
            <TabButton active={tab === 'limites'} onClick={() => setTab('limites')}>Limites por Utilização</TabButton>
            <TabButton active={tab === 'franquias'} onClick={() => setTab('franquias')}>Franquias</TabButton>
            <TabButton active={tab === 'idades'} onClick={() => setTab('idades')}>Idades</TabButton>
            <TabButton active={tab === 'sexo'} onClick={() => setTab('sexo')}>Sexo</TabButton>
            <TabButton active={tab === 'utilizacoes'} onClick={() => setTab('utilizacoes')}>Utilizações</TabButton>
            <TabButton active={tab === 'racas'} onClick={() => setTab('racas')}>Raças</TabButton>
            <TabButton active={tab === 'asininos_muares'} onClick={() => setTab('asininos_muares')}>Asininos/Muares</TabButton>
          </div>

          <div className="flex gap-2">
            {!editing && (
              <>
                <button
                  onClick={loadRules}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                >
                  <RefreshCcw size={16} />
                  Recarregar
                </button>

                <button
                  onClick={startEditing}
                  disabled={!rules}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  Editar
                </button>
              </>
            )}

            {editing && (
              <>
                <button
                  onClick={cancelEditing}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>

                <button
                  onClick={saveRules}
                  disabled={saving || !rules}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                >
                  <Save size={16} />
                  {saving ? 'Salvando...' : 'Salvar alterações'}
                </button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
            {success}
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            Carregando regras...
          </div>
        )}

        {!loading && rules && renderTabContent()}
      </div>
    </Layout>
  )
}

type TabButtonProps = {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}

function TabButton({ active, onClick, children }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg text-sm font-medium ${
        active
          ? 'bg-primary-600 text-white'
          : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
      }`}
    >
      {children}
    </button>
  )
}

type SectionProps = {
  title: string
  description?: string
  children: React.ReactNode
}

function Section({ title, description, children }: SectionProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      {description && (
        <p className="text-sm text-slate-500 mt-1 mb-6">
          {description}
        </p>
      )}
      {children}
    </div>
  )
}

type GridProps = {
  children: React.ReactNode
}

function Grid({ children }: GridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {children}
    </div>
  )
}

type InputProps = {
  label: string
  value: string | number
  onChange?: (value: string) => void
  type?: string
  disabled?: boolean
  editing?: boolean
}

function Input({
  label,
  value,
  onChange,
  type = 'text',
  disabled = false,
  editing = false
}: InputProps) {
  const displayValue = String(value ?? '')

  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </span>

      {!editing || disabled ? (
        <div className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-100 text-slate-700 min-h-[38px]">
          {displayValue || '-'}
        </div>
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
        />
      )}
    </label>
  )
}

type SmallInputProps = {
  value: string | number
  onChange: (value: string) => void
  editing?: boolean
}

function SmallInput({
  value,
  onChange,
  editing = false
}: SmallInputProps) {
  const displayValue = String(value ?? '')

  if (!editing) {
    return (
      <div className="w-full px-2 py-1 border border-slate-200 rounded text-sm bg-slate-100 text-slate-700 min-h-[30px]">
        {displayValue || '-'}
      </div>
    )
  }

  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-2 py-1 border border-slate-300 rounded text-sm"
    />
  )
}

function toNumberOrEmpty(value: string) {
  if (value === '') {
    return ''
  }

  return Number(value)
}

type EditableMapProps = {
  title: string
  description?: string
  data: Record<string, any>
  editing: boolean
  onChange: (key: string, value: string) => void
  onAdd: () => void
  onRemove: (key: string) => void
}

function EditableMap({
  title,
  description,
  data,
  editing,
  onChange,
  onAdd,
  onRemove
}: EditableMapProps) {
  const entries = Object.entries(data || {}).sort(([a], [b]) =>
    a.localeCompare(b)
  )

  return (
    <div>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-slate-900">{title}</h3>
          {description && (
            <p className="text-sm text-slate-500 mt-1">{description}</p>
          )}
        </div>

        {editing && (
          <button
            onClick={onAdd}
            className="px-3 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700"
          >
            Adicionar
          </button>
        )}
      </div>

      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-left text-slate-500">
              <th className="py-2 px-3 w-1/2">Termo</th>
              <th className="py-2 px-3 w-1/3">Código</th>
              {editing && <th className="py-2 px-3 w-24">Ações</th>}
            </tr>
          </thead>

          <tbody>
            {entries.map(([key, value]) => (
              <tr key={key} className="border-b border-slate-100 last:border-b-0">
                <td className="py-2 px-3 text-slate-700">
                  {key}
                </td>

                <td className="py-2 px-3">
                  {editing ? (
                    <input
                      value={String(value ?? '')}
                      onChange={(e) => onChange(key, e.target.value)}
                      className="w-full px-2 py-1 border border-slate-300 rounded text-sm"
                    />
                  ) : (
                    <div className="px-2 py-1 border border-slate-200 rounded bg-slate-100 text-slate-700 min-h-[30px]">
                      {String(value ?? '') || '-'}
                    </div>
                  )}
                </td>

                {editing && (
                  <td className="py-2 px-3">
                    <button
                      onClick={() => onRemove(key)}
                      className="px-2 py-1 rounded bg-red-50 text-red-700 text-xs hover:bg-red-100"
                    >
                      Remover
                    </button>
                  </td>
                )}
              </tr>
            ))}

            {entries.length === 0 && (
              <tr>
                <td
                  colSpan={editing ? 3 : 2}
                  className="py-4 px-3 text-center text-slate-500"
                >
                  Nenhum item configurado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

type EditableListProps = {
  title: string
  description?: string
  data: string[]
  editing: boolean
  onChange: (index: number, value: string) => void
  onAdd: () => void
  onRemove: (index: number) => void
}

function EditableList({
  title,
  description,
  data,
  editing,
  onChange,
  onAdd,
  onRemove
}: EditableListProps) {
  return (
    <div>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-slate-900">{title}</h3>
          {description && (
            <p className="text-sm text-slate-500 mt-1">{description}</p>
          )}
        </div>

        {editing && (
          <button
            onClick={onAdd}
            className="px-3 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700"
          >
            Adicionar
          </button>
        )}
      </div>

      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-left text-slate-500">
              <th className="py-2 px-3">Termo</th>
              {editing && <th className="py-2 px-3 w-24">Ações</th>}
            </tr>
          </thead>
          <tbody>
            {(data || []).map((value, index) => (
              <tr key={`${value}-${index}`} className="border-b border-slate-100 last:border-b-0">
                <td className="py-2 px-3">
                  {editing ? (
                    <input
                      value={String(value ?? '')}
                      onChange={(e) => onChange(index, e.target.value)}
                      className="w-full px-2 py-1 border border-slate-300 rounded text-sm"
                    />
                  ) : (
                    <div className="px-2 py-1 border border-slate-200 rounded bg-slate-100 text-slate-700 min-h-[30px]">
                      {String(value ?? '') || '-'}
                    </div>
                  )}
                </td>

                {editing && (
                  <td className="py-2 px-3">
                    <button
                      onClick={() => onRemove(index)}
                      className="px-2 py-1 rounded bg-red-50 text-red-700 text-xs hover:bg-red-100"
                    >
                      Remover
                    </button>
                  </td>
                )}
              </tr>
            ))}

            {(!data || data.length === 0) && (
              <tr>
                <td
                  colSpan={editing ? 2 : 1}
                  className="py-4 px-3 text-center text-slate-500"
                >
                  Nenhum item configurado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
