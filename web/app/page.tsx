'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ServerIcon, CameraIcon, ActivityIcon, AlertCircleIcon } from 'lucide-react'
import { api, Job, TenantUsage } from './lib/api'
import { useSession } from './components/SessionProvider'
import { useTenant } from './components/TenantProvider'

interface DashboardStats {
  totalAgents: number
  activeAgents: number
  totalSnapshots: number
  totalJobs: number
  runningJobs: number
  failedJobs: number
}

const JOB_STATUS_LABELS: Record<string, string> = {
  completed: 'Terminé',
  running: 'En cours',
  failed: 'Échoué',
  pending: 'En attente',
  ready_for_agent: "En attente de l'agent",
}

const JOB_STATUS_CLASSES: Record<string, string> = {
  completed: 'status-completed',
  running: 'status-running',
  failed: 'status-failed',
  pending: 'status-pending',
  ready_for_agent: 'status-running',
}

export default function Dashboard() {
  const router = useRouter()
  const { user } = useSession()
  const { selectedTenantId } = useTenant()
  const effectiveTenantId = user?.tenant_id ?? selectedTenantId

  const [stats, setStats] = useState<DashboardStats>({
    totalAgents: 0,
    activeAgents: 0,
    totalSnapshots: 0,
    totalJobs: 0,
    runningJobs: 0,
    failedJobs: 0
  })
  const [recentJobs, setRecentJobs] = useState<Job[]>([])
  const [usage, setUsage] = useState<TenantUsage | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardStats()
  }, [effectiveTenantId])

  const fetchDashboardStats = async () => {
    try {
      setLoading(true)
      const [agents, jobs, snapshots] = await Promise.all([
        api.getAgents(effectiveTenantId ?? undefined),
        api.getJobs(undefined, effectiveTenantId ?? undefined),
        api.getSnapshots(effectiveTenantId ?? undefined),
      ])

      setStats({
        totalAgents: agents.length,
        activeAgents: agents.filter((a) => a.status === 'active').length,
        totalSnapshots: snapshots.length,
        totalJobs: jobs.length,
        runningJobs: jobs.filter((j) => j.status === 'running' || j.status === 'ready_for_agent').length,
        failedJobs: jobs.filter((j) => j.status === 'failed').length,
      })
      setRecentJobs(
        [...jobs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 3)
      )

      if (effectiveTenantId !== null && effectiveTenantId !== undefined) {
        try {
          setUsage(await api.getTenantUsage(effectiveTenantId))
        } catch (error) {
          console.error("Erreur lors de la récupération de l'utilisation du tenant:", error)
        }
      }
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

  const quotaBarColor = !usage ? 'bg-primary-500'
    : usage.quota_percent >= 90 ? 'bg-error-500'
    : usage.quota_percent >= 70 ? 'bg-warning-500'
    : 'bg-success-500'

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

      {/* Utilisation du quota (voir docs/adr/0006-facturation-quotas.md) */}
      {usage && (
        <div className="card mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold text-gray-900">Utilisation du tenant</h2>
            <span className="text-sm text-gray-500">
              {(usage.used_bytes / 1e9).toFixed(2)} GB / {(usage.quota_bytes / 1e9).toFixed(2)} GB
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div
              className={`h-3 rounded-full ${quotaBarColor}`}
              style={{ width: `${Math.min(usage.quota_percent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">
            {usage.quota_percent.toFixed(1)}% du quota utilisé — coût estimé : {usage.estimated_cost.toFixed(2)} $
          </p>
        </div>
      )}

      {/* Actions rapides */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Actions rapides
          </h2>
          <div className="space-y-3">
            <button onClick={() => router.push('/downloads')} className="btn-primary w-full text-left">
              📥 Télécharger un agent
            </button>
            <button onClick={() => router.push('/agents')} className="btn-secondary w-full text-left">
              🔍 Voir tous les agents
            </button>
            <button onClick={() => router.push('/snapshots')} className="btn-secondary w-full text-left">
              📸 Parcourir les snapshots
            </button>
            <button onClick={() => router.push('/settings')} className="btn-secondary w-full text-left">
              ⚙️ Paramètres système
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Activité récente
          </h2>
          {recentJobs.length === 0 ? (
            <p className="text-sm text-gray-500">Aucune activité pour l'instant.</p>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job, index) => (
                <div
                  key={job.id}
                  className={`flex items-center justify-between py-2 ${index < recentJobs.length - 1 ? 'border-b border-gray-100' : ''}`}
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      Job {job.type} #{job.id}
                    </p>
                    <p className="text-xs text-gray-500">Agent #{job.agent_id}</p>
                  </div>
                  <span className={`status-badge ${JOB_STATUS_CLASSES[job.status] || 'status-inactive'}`}>
                    {JOB_STATUS_LABELS[job.status] || job.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
