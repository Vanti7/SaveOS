'use client'

import { useEffect, useState } from 'react'
import { XIcon, Loader2Icon } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import toast from 'react-hot-toast'
import { api, Agent, AgentDetail } from '../lib/api'

interface AgentDetailModalProps {
  agent: Agent
  onClose: () => void
}

const formatBytes = (bytes: number) => {
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  if (bytes === 0) return '0 B'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

export default function AgentDetailModal({ agent, onClose }: AgentDetailModalProps) {
  const [detail, setDetail] = useState<AgentDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api.getAgentDetail(agent.id)
      .then((data) => { if (!cancelled) setDetail(data) })
      .catch(() => { if (!cancelled) toast.error("Erreur lors de la récupération des détails de l'agent") })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [agent.id])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{agent.hostname}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2Icon className="w-6 h-6 animate-spin text-primary-600" />
            </div>
          ) : detail ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Plateforme</dt>
                <dd className="text-gray-900 capitalize">{detail.platform}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Statut</dt>
                <dd className="text-gray-900">{detail.status}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Dernière activité</dt>
                <dd className="text-gray-900">
                  {formatDistanceToNow(new Date(detail.last_seen), { addSuffix: true, locale: fr })}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Créé</dt>
                <dd className="text-gray-900">
                  {formatDistanceToNow(new Date(detail.created_at), { addSuffix: true, locale: fr })}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Snapshots</dt>
                <dd className="text-gray-900">{detail.total_snapshots}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Volume sauvegardé</dt>
                <dd className="text-gray-900">{formatBytes(detail.total_size_bytes)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Dernière sauvegarde</dt>
                <dd className="text-gray-900">
                  {detail.last_backup
                    ? formatDistanceToNow(new Date(detail.last_backup), { addSuffix: true, locale: fr })
                    : 'Aucune'}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-gray-500 py-8 text-center">Détails indisponibles</p>
          )}
        </div>

        <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">Fermer</button>
        </div>
      </div>
    </div>
  )
}
