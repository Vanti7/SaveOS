'use client'

import { useEffect, useState } from 'react'
import { ServerIcon, CameraIcon, ActivityIcon, AlertCircleIcon } from 'lucide-react'
import { apiClient } from './lib/api'

interface DashboardStats {
  totalAgents: number
  activeAgents: number
  totalSnapshots: number
  totalJobs: number
  runningJobs: number
  failedJobs: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalAgents: 0,
    activeAgents: 0,
    totalSnapshots: 0,
    totalJobs: 0,
    runningJobs: 0,
    failedJobs: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardStats()
  }, [])

  const fetchDashboardStats = async () => {
    try {
      // Pour le MVP, on simule les stats
      // Dans une vraie implémentation, on ferait appel à l'API
      setStats({
        totalAgents: 3,
        activeAgents: 2,
        totalSnapshots: 15,
        totalJobs: 25,
        runningJobs: 1,
        failedJobs: 2
      })
    } catch (error) {
      console.error('Erreur lors de la récupération des stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const StatCard = ({ 
    title, 
    value, 
    icon: Icon, 
    color = 'primary',
    subtitle 
  }: {
    title: string
    value: number | string
    icon: any
    color?: 'primary' | 'success' | 'warning' | 'error'
    subtitle?: string
  }) => (
    <div className="card">
      <div className="flex items-center">
        <div className={`p-3 rounded-full bg-${color}-100`}>
          <Icon className={`w-6 h-6 text-${color}-600`} />
        </div>
        <div className="ml-4">
          <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
          <p className="text-sm text-gray-600">{title}</p>
          {subtitle && (
            <p className="text-xs text-gray-500">{subtitle}</p>
          )}
        </div>
      </div>
    </div>
  )

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
        <h1 className="text-3xl font-bold text-gray-900">Dashboard SaveOS</h1>
        <p className="text-gray-600 mt-2">
          Vue d'ensemble de votre système de sauvegarde centralisé
        </p>
      </div>

      {/* Stats principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Agents totaux"
          value={stats.totalAgents}
          icon={ServerIcon}
          color="primary"
          subtitle={`${stats.activeAgents} actifs`}
        />
        
        <StatCard
          title="Snapshots"
          value={stats.totalSnapshots}
          icon={CameraIcon}
          color="success"
        />
        
        <StatCard
          title="Jobs en cours"
          value={stats.runningJobs}
          icon={ActivityIcon}
          color="warning"
          subtitle={`${stats.totalJobs} au total`}
        />
        
        <StatCard
          title="Jobs échoués"
          value={stats.failedJobs}
          icon={AlertCircleIcon}
          color="error"
        />
      </div>

      {/* Actions rapides */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Actions rapides
          </h2>
          <div className="space-y-3">
            <button className="btn-primary w-full text-left">
              📥 Télécharger un agent
            </button>
            <button className="btn-secondary w-full text-left">
              🔍 Voir tous les agents
            </button>
            <button className="btn-secondary w-full text-left">
              📸 Parcourir les snapshots
            </button>
            <button className="btn-secondary w-full text-left">
              ⚙️ Paramètres système
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Activité récente
          </h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Sauvegarde terminée
                </p>
                <p className="text-xs text-gray-500">Agent: DESKTOP-ABC123</p>
              </div>
              <span className="status-badge status-completed">Terminé</span>
            </div>
            
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Nouvel agent enregistré
                </p>
                <p className="text-xs text-gray-500">Agent: MacBook-Pro</p>
              </div>
              <span className="status-badge status-active">Actif</span>
            </div>
            
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Sauvegarde échouée
                </p>
                <p className="text-xs text-gray-500">Agent: Ubuntu-Server</p>
              </div>
              <span className="status-badge status-failed">Échoué</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}