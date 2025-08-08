'use client'

import { useEffect, useState } from 'react'
import { PlusIcon, RefreshCwIcon, ServerIcon } from 'lucide-react'
import { api, Agent } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import toast from 'react-hot-toast'

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const data = await api.getAgents()
      setAgents(data)
    } catch (error) {
      console.error('Erreur lors de la récupération des agents:', error)
      toast.error('Erreur lors de la récupération des agents')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'status-active'
      case 'inactive':
        return 'status-inactive'
      case 'error':
        return 'status-error'
      default:
        return 'status-inactive'
    }
  }

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'windows':
        return '🪟'
      case 'darwin':
      case 'macos':
        return '🍎'
      case 'linux':
        return '🐧'
      default:
        return '💻'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return 'Actif'
      case 'inactive':
        return 'Inactif'
      case 'error':
        return 'Erreur'
      default:
        return 'Inconnu'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agents de sauvegarde</h1>
          <p className="text-gray-600 mt-2">
            Gérez vos agents de sauvegarde sur différentes machines
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={fetchAgents}
            className="btn-secondary flex items-center"
          >
            <RefreshCwIcon className="w-4 h-4 mr-2" />
            Actualiser
          </button>
          <button className="btn-primary flex items-center">
            <PlusIcon className="w-4 h-4 mr-2" />
            Ajouter un agent
          </button>
        </div>
      </div>

      {/* Statistiques rapides */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <ServerIcon className="w-8 h-8 text-primary-600" />
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">{agents.length}</h3>
              <p className="text-sm text-gray-600">Agents totaux</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-success-100 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-success-500"></div>
            </div>
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">
                {agents.filter(a => a.status === 'active').length}
              </h3>
              <p className="text-sm text-gray-600">Agents actifs</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-error-100 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-error-500"></div>
            </div>
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">
                {agents.filter(a => a.status === 'error').length}
              </h3>
              <p className="text-sm text-gray-600">Agents en erreur</p>
            </div>
          </div>
        </div>
      </div>

      {/* Liste des agents */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Plateforme
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Dernière activité
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Créé le
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {agents.map((agent) => (
                <tr key={agent.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <ServerIcon className="w-5 h-5 text-gray-400 mr-3" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {agent.hostname}
                        </div>
                        <div className="text-sm text-gray-500">ID: {agent.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="text-lg mr-2">
                        {getPlatformIcon(agent.platform)}
                      </span>
                      <span className="text-sm text-gray-900 capitalize">
                        {agent.platform}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`status-badge ${getStatusColor(agent.status)}`}>
                      {getStatusText(agent.status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDistanceToNow(new Date(agent.last_seen), { 
                      addSuffix: true, 
                      locale: fr 
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDistanceToNow(new Date(agent.created_at), { 
                      addSuffix: true, 
                      locale: fr 
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button className="text-primary-600 hover:text-primary-900 mr-3">
                      Détails
                    </button>
                    <button className="text-warning-600 hover:text-warning-900 mr-3">
                      Configurer
                    </button>
                    <button className="text-error-600 hover:text-error-900">
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {agents.length === 0 && (
          <div className="text-center py-12">
            <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              Aucun agent enregistré
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Commencez par télécharger et installer un agent sur vos machines.
            </p>
            <div className="mt-6">
              <button className="btn-primary">
                Télécharger un agent
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}