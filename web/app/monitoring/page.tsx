'use client'

import { useEffect, useState } from 'react'
import { ActivityIcon, AlertTriangleIcon, CheckCircleIcon, ClockIcon } from 'lucide-react'
import { api, Job } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import toast from 'react-hot-toast'

export default function MonitoringPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchJobs()
    // Actualiser toutes les 30 secondes
    const interval = setInterval(fetchJobs, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchJobs = async () => {
    try {
      setLoading(true)
      const data = await api.getJobs()
      setJobs(data)
    } catch (error) {
      console.error('Erreur lors de la récupération des jobs:', error)
      toast.error('Erreur lors de la récupération des jobs')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-success-500" />
      case 'running':
        return <ActivityIcon className="w-5 h-5 text-primary-500 animate-pulse" />
      case 'failed':
        return <AlertTriangleIcon className="w-5 h-5 text-error-500" />
      default:
        return <ClockIcon className="w-5 h-5 text-warning-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed'
      case 'running':
        return 'status-running'
      case 'failed':
        return 'status-failed'
      case 'pending':
        return 'status-pending'
      default:
        return 'status-inactive'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Terminé'
      case 'running':
        return 'En cours'
      case 'failed':
        return 'Échoué'
      case 'pending':
        return 'En attente'
      default:
        return 'Inconnu'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'backup':
        return '💾'
      case 'restore':
        return '📥'
      case 'check':
        return '🔍'
      default:
        return '❓'
    }
  }

  const getTypeText = (type: string) => {
    switch (type) {
      case 'backup':
        return 'Sauvegarde'
      case 'restore':
        return 'Restauration'
      case 'check':
        return 'Vérification'
      default:
        return 'Inconnu'
    }
  }

  const formatDuration = (startedAt?: string, finishedAt?: string) => {
    if (!startedAt) return '-'
    
    const start = new Date(startedAt)
    const end = finishedAt ? new Date(finishedAt) : new Date()
    const duration = Math.floor((end.getTime() - start.getTime()) / 1000)
    
    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const runningJobs = jobs.filter(j => j.status === 'running')
  const completedJobs = jobs.filter(j => j.status === 'completed')
  const failedJobs = jobs.filter(j => j.status === 'failed')

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Monitoring des jobs</h1>
          <p className="text-gray-600 mt-2">
            Surveillez l'état de vos jobs de sauvegarde en temps réel
          </p>
        </div>
        <button
          onClick={fetchJobs}
          className="btn-secondary flex items-center"
        >
          <ActivityIcon className="w-4 h-4 mr-2" />
          Actualiser
        </button>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <ActivityIcon className="w-8 h-8 text-primary-600" />
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">{jobs.length}</h3>
              <p className="text-sm text-gray-600">Jobs totaux</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-warning-100 flex items-center justify-center">
              <ActivityIcon className="w-4 h-4 text-warning-600 animate-pulse" />
            </div>
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">{runningJobs.length}</h3>
              <p className="text-sm text-gray-600">En cours</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <CheckCircleIcon className="w-8 h-8 text-success-600" />
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">{completedJobs.length}</h3>
              <p className="text-sm text-gray-600">Terminés</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <AlertTriangleIcon className="w-8 h-8 text-error-600" />
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">{failedJobs.length}</h3>
              <p className="text-sm text-gray-600">Échoués</p>
            </div>
          </div>
        </div>
      </div>

      {/* Jobs en cours */}
      {runningJobs.length > 0 && (
        <div className="card mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Jobs en cours d'exécution
          </h2>
          <div className="space-y-4">
            {runningJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between p-4 bg-primary-50 rounded-lg">
                <div className="flex items-center">
                  <div className="text-2xl mr-3">{getTypeIcon(job.type)}</div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-900">
                      {getTypeText(job.type)} - Agent {job.agent_id}
                    </h3>
                    <p className="text-xs text-gray-500">
                      Démarré {formatDistanceToNow(new Date(job.started_at!), { addSuffix: true, locale: fr })}
                    </p>
                  </div>
                </div>
                <div className="flex items-center">
                  <div className="text-right mr-4">
                    <p className="text-sm font-medium text-gray-900">
                      {formatDuration(job.started_at)}
                    </p>
                    <p className="text-xs text-gray-500">Durée</p>
                  </div>
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historique des jobs */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Historique des jobs
        </h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Job
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Durée
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
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(job.status)}
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-900">
                          Job #{job.id}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="text-lg mr-2">{getTypeIcon(job.type)}</span>
                      <span className="text-sm text-gray-900">
                        {getTypeText(job.type)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`status-badge ${getStatusColor(job.status)}`}>
                      {getStatusText(job.status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    Agent {job.agent_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDuration(job.started_at, job.finished_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDistanceToNow(new Date(job.created_at), { 
                      addSuffix: true, 
                      locale: fr 
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button className="text-primary-600 hover:text-primary-900 mr-3">
                      Détails
                    </button>
                    {job.status === 'failed' && (
                      <button className="text-warning-600 hover:text-warning-900">
                        Relancer
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {jobs.length === 0 && (
          <div className="text-center py-12">
            <ActivityIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              Aucun job trouvé
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Les jobs apparaîtront ici dès qu'ils seront créés.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}