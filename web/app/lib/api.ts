import axios from 'axios'
import fileDownload from 'js-file-download'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:8000'

// Configuration d'axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Vérifie le certificat TLS sauf pour les hôtes de dev connus
// (localhost/127.0.0.1, certificat self-signed généré par
// scripts/generate_certs.sh) — voir docs/adr/0003-certificats-tls-production.md.
const API_HOSTNAME = new URL(API_BASE_URL).hostname
const SHOULD_VERIFY_SSL = !['localhost', '127.0.0.1'].includes(API_HOSTNAME)
apiClient.defaults.httpsAgent = new (require('https').Agent)({
  rejectUnauthorized: SHOULD_VERIFY_SSL
})

// Client vers les routes proxy Next.js (web/app/api/**), sans baseURL : les
// chemins relatifs résolvent vers l'origine de la page (jamais l'API
// distante directement). Ces routes portent le token dashboard côté
// serveur uniquement — voir web/app/lib/serverApi.ts.
const dashboardClient = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types pour l'API
export interface Agent {
  id: number
  hostname: string
  platform: string
  status: 'active' | 'inactive' | 'error'
  last_seen: string
  created_at: string
}

export interface Job {
  id: number
  agent_id: number
  type: 'backup' | 'restore' | 'check'
  status: 'pending' | 'running' | 'ready_for_agent' | 'completed' | 'failed'
  started_at?: string
  finished_at?: string
  error_message?: string
  created_at: string
}

export interface Snapshot {
  id: number
  job_id: number
  agent_id: number
  name: string
  repo_path: string
  size_bytes: number
  is_full: boolean
  created_at: string
}

export interface ArchiveEntry {
  path: string
  type?: string
  size?: number
  mtime?: string
}

export interface ArchiveBrowseResponse {
  path: string
  entries: ArchiveEntry[]
}

export interface Tenant {
  id: number
  name: string
  quota_bytes: number
  retention_policy: string
  created_at: string
}

export interface TenantCreateResponse extends Tenant {
  registration_secret: string // en clair, une seule fois
}

export interface User {
  id: number
  email: string
  role: 'admin' | 'user'
  tenant_id: number
  created_at: string
}

export type RestoreTarget = 'download' | 'agent'

export interface RestoreJobCreate {
  agent_id: number
  snapshot_id: number
  selected_paths: string[]
  target: RestoreTarget
  restore_path?: string
}

// API Functions
export const api = {
  // Santé de l'API
  async healthCheck() {
    const response = await apiClient.get('/health')
    return response.data
  },

  // Métriques
  async getMetrics() {
    const response = await apiClient.get('/metrics')
    return response.data
  },

  // Agents
  async getAgents(tenantId?: number): Promise<Agent[]> {
    const response = await dashboardClient.get('/api/agents', {
      params: tenantId ? { tenant_id: tenantId } : {},
    })
    return response.data
  },

  // Jobs
  async getJobs(agentId?: number, tenantId?: number): Promise<Job[]> {
    const response = await dashboardClient.get('/api/jobs', {
      params: {
        ...(agentId ? { agent_id: agentId } : {}),
        ...(tenantId ? { tenant_id: tenantId } : {}),
      },
    })
    return response.data
  },

  // Job unique (pour le suivi de statut d'une restauration en cours)
  async getJob(jobId: number): Promise<Job> {
    const response = await dashboardClient.get(`/api/jobs/${jobId}`)
    return response.data
  },

  // Snapshots
  async getSnapshots(tenantId?: number): Promise<Snapshot[]> {
    const response = await dashboardClient.get('/api/snapshots', {
      params: tenantId ? { tenant_id: tenantId } : {},
    })
    return response.data
  },

  // Tenants (multi-tenancy — voir docs/adr/0004-multi-tenancy-avancee.md)
  async getTenants(): Promise<Tenant[]> {
    const response = await dashboardClient.get('/api/tenants')
    return response.data
  },

  async createTenant(name: string, quotaBytes?: number, retentionPolicy?: Record<string, number>): Promise<TenantCreateResponse> {
    const response = await dashboardClient.post('/api/tenants', {
      name,
      ...(quotaBytes !== undefined ? { quota_bytes: quotaBytes } : {}),
      ...(retentionPolicy !== undefined ? { retention_policy: retentionPolicy } : {}),
    })
    return response.data
  },

  // Connexion / session (voir docs/adr/0005-gestion-utilisateurs-roles.md)
  async login(email: string, password: string): Promise<{ user: User }> {
    const response = await dashboardClient.post('/api/auth/login', { email, password })
    return response.data
  },

  async logout(): Promise<void> {
    await dashboardClient.post('/api/auth/logout')
  },

  async getCurrentUser(): Promise<User> {
    const response = await dashboardClient.get('/api/auth/me')
    return response.data
  },

  // Utilisateurs (admin uniquement, toujours limité à son propre tenant)
  async getUsers(): Promise<User[]> {
    const response = await dashboardClient.get('/api/users')
    return response.data
  },

  async createUser(email: string, password: string, role: 'admin' | 'user' = 'user'): Promise<User> {
    const response = await dashboardClient.post('/api/users', { email, password, role })
    return response.data
  },

  // Parcourt le contenu d'un snapshot à un chemin donné (un niveau de dossier à la fois)
  async browseSnapshot(snapshotId: number, agentId: number, path: string = ''): Promise<ArchiveBrowseResponse> {
    const response = await dashboardClient.post(`/api/snapshots/${snapshotId}/browse`, {
      agent_id: agentId,
      path,
    })
    return response.data
  },

  // Crée un job de restauration granulaire
  async createRestoreJob(payload: RestoreJobCreate): Promise<Job> {
    const response = await dashboardClient.post('/api/restore', payload)
    return response.data
  },

  // Télécharge le paquet résultant d'une restauration terminée
  async downloadRestorePackage(jobId: number, filename: string): Promise<void> {
    const response = await dashboardClient.get(`/api/restore/${jobId}/download`, {
      responseType: 'blob',
    })
    fileDownload(response.data, filename)
  },

  // Téléchargement d'agent (package source, zip/tar.gz). registrationSecret
  // est embarqué dans le config.json du package (nécessaire à l'auto-
  // enregistrement de l'agent installé, voir
  // docs/adr/0004-multi-tenancy-avancee.md).
  async downloadAgent(platform: string, registrationSecret?: string): Promise<Blob> {
    const response = await apiClient.get(`/download/agent/${platform}`, {
      params: registrationSecret ? { registration_secret: registrationSecret } : {},
      responseType: 'blob'
    })
    return response.data
  },

  // URL de l'installeur natif (exe/dmg/deb) : simple redirection HTTP côté
  // API, pas de fetch nécessaire — un lien direct suffit.
  installerDownloadUrl(platform: string): string {
    return `${API_BASE_URL}/download/agent/${platform}/installer`
  },

  // Provisionne un agent (token pré-généré) pour un tenant explicite, avant
  // de générer son package. Passe par la route proxy (tenant_id exige
  // désormais le token dashboard, jamais accessible depuis le navigateur —
  // voir docs/adr/0004-multi-tenancy-avancee.md).
  async provisionAgent(hostname: string, platform: string, tenantId: number) {
    const response = await dashboardClient.post('/api/agents/provision', null, {
      params: { hostname, platform, tenant_id: tenantId },
    })
    return response.data
  },

  // Configuration d'agent
  async generateAgentConfig(hostname: string, platform: string) {
    return {
      api_url: API_BASE_URL,
      hostname,
      platform,
      token: `agent_token_${Date.now()}`, // Token temporaire
      verify_ssl: SHOULD_VERIFY_SSL
    }
  }
}

export { apiClient }