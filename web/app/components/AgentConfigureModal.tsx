'use client'

import { useState } from 'react'
import { XIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Agent } from '../lib/api'

interface AgentConfigureModalProps {
  agent: Agent
  onClose: () => void
  onSaved: (agent: Agent) => void
}

export default function AgentConfigureModal({ agent, onClose, onSaved }: AgentConfigureModalProps) {
  const [hostname, setHostname] = useState(agent.hostname)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    const trimmed = hostname.trim()
    if (!trimmed) {
      toast.error('Le hostname ne peut pas être vide')
      return
    }
    setSaving(true)
    try {
      const updated = await api.updateAgent(agent.id, { hostname: trimmed })
      toast.success('Agent mis à jour')
      onSaved(updated)
      onClose()
    } catch (error: any) {
      const detail = error?.response?.data?.error || "Erreur lors de la mise à jour de l'agent"
      toast.error(detail)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Configurer l'agent</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Hostname</label>
          <input
            type="text"
            className="input-field"
            value={hostname}
            onChange={(e) => setHostname(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">Annuler</button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Enregistrement...' : 'Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  )
}
