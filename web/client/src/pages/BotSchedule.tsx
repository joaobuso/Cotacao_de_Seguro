import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { Plus, Save, Trash2, RefreshCcw } from 'lucide-react'

type Slot = {
  id: string
  descricao: string
  active: boolean
  days: number[]
  start: string
  end: string
}

type Schedule = {
  _id?: string
  enabled: boolean
  timezone: string
  sendAutoMessageWhenInactive: boolean
  inactiveMessage: string
  slots: Slot[]
}

const WEEK_DAYS = [
  { id: 0, label: 'Seg' },
  { id: 1, label: 'Ter' },
  { id: 2, label: 'Qua' },
  { id: 3, label: 'Qui' },
  { id: 4, label: 'Sex' },
  { id: 5, label: 'Sáb' },
  { id: 6, label: 'Dom' },
]

export default function BotSchedule() {
  const [schedule, setSchedule] = useState<Schedule | null>(null)
  const [original, setOriginal] = useState<Schedule | null>(null)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function loadSchedule() {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/bot/schedule', {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error(`Erro ao buscar horários: HTTP ${response.status}`)
      }

      const data = await response.json()
      setSchedule(data)
      setOriginal(structuredClone(data))
      setEditing(false)
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar horários')
    } finally {
      setLoading(false)
    }
  }

  async function saveSchedule() {
    if (!schedule) return

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/bot/schedule', {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(schedule)
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`Erro ao salvar horários: HTTP ${response.status} - ${text}`)
      }

      setSuccess('Horários salvos com sucesso.')
      setOriginal(structuredClone(schedule))
      setEditing(false)
    } catch (err: any) {
      setError(err.message || 'Erro ao salvar horários')
    } finally {
      setSaving(false)
    }
  }

  function cancelEditing() {
    if (original) {
      setSchedule(structuredClone(original))
    }

    setEditing(false)
    setError(null)
    setSuccess(null)
  }

  function updateField(field: keyof Schedule, value: any) {
    setSchedule((prev) => {
      if (!prev) return prev

      return {
        ...prev,
        [field]: value
      }
    })
  }

  function updateSlot(index: number, field: keyof Slot, value: any) {
    setSchedule((prev) => {
      if (!prev) return prev

      const slots = [...prev.slots]
      slots[index] = {
        ...slots[index],
        [field]: value
      }

      return {
        ...prev,
        slots
      }
    })
  }

  function toggleDay(slotIndex: number, day: number) {
    if (!schedule) return

    const slot = schedule.slots[slotIndex]
    const hasDay = slot.days.includes(day)

    const newDays = hasDay
      ? slot.days.filter((d) => d !== day)
      : [...slot.days, day].sort()

    updateSlot(slotIndex, 'days', newDays)
  }

  function addSlot() {
    if (!schedule) return

    const newSlot: Slot = {
      id: `horario_${Date.now()}`,
      descricao: 'Novo horário',
      active: true,
      days: [0, 1, 2, 3, 4],
      start: '18:00',
      end: '09:00'
    }

    setSchedule({
      ...schedule,
      slots: [...schedule.slots, newSlot]
    })
  }

  function removeSlot(index: number) {
    if (!schedule) return
    if (!window.confirm('Remover este horário?')) return

    setSchedule({
      ...schedule,
      slots: schedule.slots.filter((_, i) => i !== index)
    })
  }

  useEffect(() => {
    loadSchedule()
  }, [])

  return (
    <Layout
      title="Horário de Atuação do Bot"
      subtitle="Configure quando o bot responderá automaticamente e quando o atendimento será humano."
    >
      <div className="space-y-6">
        <div className="flex justify-end gap-2">
          {!editing && (
            <>
              <button
                onClick={loadSchedule}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              >
                <RefreshCcw size={16} />
                Recarregar
              </button>

              <button
                onClick={() => setEditing(true)}
                className="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
              >
                Editar
              </button>
            </>
          )}

          {editing && (
            <>
              <button
                onClick={cancelEditing}
                className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>

              <button
                onClick={saveSchedule}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
              >
                <Save size={16} />
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </>
          )}
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
            Carregando horários...
          </div>
        )}

        {!loading && schedule && (
          <>
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">
                Configurações gerais
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <ReadOrInput
                  label="Configuração ativa"
                  value={schedule.enabled ? 'Sim' : 'Não'}
                  editing={editing}
                  type="select"
                  options={[
                    { label: 'Sim', value: 'true' },
                    { label: 'Não', value: 'false' }
                  ]}
                  onChange={(v) => updateField('enabled', v === 'true')}
                />

                <ReadOrInput
                  label="Fuso horário"
                  value={schedule.timezone}
                  editing={editing}
                  onChange={(v) => updateField('timezone', v)}
                />

                <ReadOrInput
                  label="Enviar mensagem automática fora do horário do bot"
                  value={schedule.sendAutoMessageWhenInactive ? 'Sim' : 'Não'}
                  editing={editing}
                  type="select"
                  options={[
                    { label: 'Sim', value: 'true' },
                    { label: 'Não', value: 'false' }
                  ]}
                  onChange={(v) => updateField('sendAutoMessageWhenInactive', v === 'true')}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Mensagem automática fora do horário do bot
                </label>

                {editing ? (
                  <textarea
                    value={schedule.inactiveMessage}
                    onChange={(e) => updateField('inactiveMessage', e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                ) : (
                  <div className="whitespace-pre-wrap px-3 py-2 border border-slate-200 rounded-lg bg-slate-100 text-slate-700 text-sm">
                    {schedule.inactiveMessage || '-'}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    Períodos em que o bot atua
                  </h2>
                  <p className="text-sm text-slate-500">
                    Fora desses horários, as mensagens serão direcionadas para atendimento humano.
                  </p>
                </div>

                {editing && (
                  <button
                    onClick={addSlot}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
                  >
                    <Plus size={16} />
                    Adicionar horário
                  </button>
                )}
              </div>

              <div className="space-y-4">
                {schedule.slots.map((slot, index) => (
                  <div
                    key={slot.id || index}
                    className="border border-slate-200 rounded-lg p-4 space-y-4"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                      <ReadOrInput
                        label="Descrição"
                        value={slot.descricao}
                        editing={editing}
                        onChange={(v) => updateSlot(index, 'descricao', v)}
                      />

                      <ReadOrInput
                        label="Ativo"
                        value={slot.active ? 'Sim' : 'Não'}
                        editing={editing}
                        type="select"
                        options={[
                          { label: 'Sim', value: 'true' },
                          { label: 'Não', value: 'false' }
                        ]}
                        onChange={(v) => updateSlot(index, 'active', v === 'true')}
                      />

                      <ReadOrInput
                        label="Início"
                        value={slot.start}
                        editing={editing}
                        type="time"
                        onChange={(v) => updateSlot(index, 'start', v)}
                      />

                      <ReadOrInput
                        label="Fim"
                        value={slot.end}
                        editing={editing}
                        type="time"
                        onChange={(v) => updateSlot(index, 'end', v)}
                      />

                      {editing && (
                        <div className="flex items-end">
                          <button
                            onClick={() => removeSlot(index)}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100"
                          >
                            <Trash2 size={16} />
                            Remover
                          </button>
                        </div>
                      )}
                    </div>

                    <div>
                      <p className="text-sm font-medium text-slate-700 mb-2">
                        Dias da semana
                      </p>

                      <div className="flex flex-wrap gap-2">
                        {WEEK_DAYS.map((day) => {
                          const active = slot.days.includes(day.id)

                          return (
                            <button
                              key={day.id}
                              disabled={!editing}
                              onClick={() => toggleDay(index, day.id)}
                              className={`px-3 py-2 rounded-lg text-sm border ${
                                active
                                  ? 'bg-primary-600 text-white border-primary-600'
                                  : 'bg-white text-slate-600 border-slate-300'
                              } disabled:opacity-80`}
                            >
                              {day.label}
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    <div className="text-sm text-slate-500">
                      {slot.start > slot.end
                        ? 'Este horário cruza a meia-noite.'
                        : 'Este horário começa e termina no mesmo dia.'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}

type Option = {
  label: string
  value: string
}

type ReadOrInputProps = {
  label: string
  value: string
  editing: boolean
  onChange: (value: string) => void
  type?: 'text' | 'time' | 'select'
  options?: Option[]
}

function ReadOrInput({
  label,
  value,
  editing,
  onChange,
  type = 'text',
  options = []
}: ReadOrInputProps) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </span>

      {!editing ? (
        <div className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-100 text-slate-700 min-h-[38px]">
          {value || '-'}
        </div>
      ) : type === 'select' ? (
        <select
          value={String(value === 'Sim' ? 'true' : value === 'Não' ? 'false' : value)}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
        />
      )}
    </label>
  )
}