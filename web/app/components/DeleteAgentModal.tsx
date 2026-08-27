'use client'

import { useState } from 'react'
import { AlertTriangleIcon, XIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Agent } from '../lib/api'

interface DeleteAgentModalProps {
  agent: Agent
  onClose: () => void
  onDeleted: (agentId: number) => void
}

export default function DeleteAgentModal({ agent, onClose, onDeleted }: DeleteAgentModalProps) {
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await api.deleteAgent(agent.id)
      toast.success('Agent supprimé')
      onDeleted(agent.id)
      onClose()
    } catch (error: any) {
      const detail = error?.response?.data?.error || "Erreur lors de la suppression de l'agent"
      toast.error(detail)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Supprimer l'agent</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4">
          <div className="flex items-start gap-3">
            <AlertTriangleIcon className="w-8 h-8 text-error-500 shrink-0" />
            <p className="text-sm text-gray-700">
              Supprimer <strong>{agent.hostname}</strong> supprime aussi définitivement son historique de
              jobs et de snapshots de SaveOS. Les données déjà sauvegardées par Borg restent sur le
              disque de stockage mais ne seront plus visibles ni restaurables depuis le tableau de bord.
              Cette action est irréversible.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">Annuler</button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="btn-error disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deleting ? 'Suppression...' : 'Supprimer définitivement'}
          </button>
        </div>
      </div>
    </div>
  )
}
