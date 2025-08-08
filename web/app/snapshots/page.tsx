'use client'

import { useEffect, useState } from 'react'
import { CameraIcon, DownloadIcon, FolderIcon } from 'lucide-react'
import { api, Snapshot } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import toast from 'react-hot-toast'

export default function SnapshotsPage() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSnapshots()
  }, [])

  const fetchSnapshots = async () => {
    try {
      setLoading(true)
      const data = await api.getSnapshots()
      setSnapshots(data)
    } catch (error) {
      console.error('Erreur lors de la récupération des snapshots:', error)
      toast.error('Erreur lors de la récupération des snapshots')
    } finally {
      setLoading(false)
    }
  }

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    if (bytes === 0) return '0 B'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Snapshots de sauvegarde</h1>
        <p className="text-gray-600 mt-2">
          Parcourez et gérez vos snapshots de sauvegarde
        </p>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <CameraIcon className="w-8 h-8 text-primary-600" />
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">{snapshots.length}</h3>
              <p className="text-sm text-gray-600">Snapshots totaux</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <FolderIcon className="w-8 h-8 text-success-600" />
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">
                {formatBytes(snapshots.reduce((acc, s) => acc + s.size_bytes, 0))}
              </h3>
              <p className="text-sm text-gray-600">Taille totale</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-primary-500"></div>
            </div>
            <div className="ml-4">
              <h3 className="text-2xl font-bold text-gray-900">
                {snapshots.filter(s => s.is_full).length}
              </h3>
              <p className="text-sm text-gray-600">Sauvegardes complètes</p>
            </div>
          </div>
        </div>
      </div>

      {/* Liste des snapshots */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Snapshot
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Taille
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Repository
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
              {snapshots.map((snapshot) => (
                <tr key={snapshot.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <CameraIcon className="w-5 h-5 text-gray-400 mr-3" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {snapshot.name}
                        </div>
                        <div className="text-sm text-gray-500">ID: {snapshot.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`status-badge ${snapshot.is_full ? 'status-active' : 'status-warning'}`}>
                      {snapshot.is_full ? 'Complète' : 'Incrémentale'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatBytes(snapshot.size_bytes)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 font-mono">
                      {snapshot.repo_path.split('/').pop()}
                    </div>
                    <div className="text-xs text-gray-500">
                      Job: {snapshot.job_id}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDistanceToNow(new Date(snapshot.created_at), { 
                      addSuffix: true, 
                      locale: fr 
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button className="text-primary-600 hover:text-primary-900 mr-3">
                      Parcourir
                    </button>
                    <button className="text-success-600 hover:text-success-900 mr-3">
                      <DownloadIcon className="w-4 h-4 inline mr-1" />
                      Restaurer
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

        {snapshots.length === 0 && (
          <div className="text-center py-12">
            <CameraIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              Aucun snapshot trouvé
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Les snapshots apparaîtront ici après vos premières sauvegardes.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}