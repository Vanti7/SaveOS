import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:8000'

// Configuration d'axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Pour le MVP, on désactive la vérification SSL
apiClient.defaults.httpsAgent = new (require('https').Agent)({
  rejectUnauthorized: false
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
  status: 'pending' | 'running' | 'completed' | 'failed'
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
  async getAgents(): Promise<Agent[]> {
    const response = await dashboardClient.get('/api/agents')
    return response.data
  },

  // Jobs
  async getJobs(agentId?: number): Promise<Job[]> {
    const response = await dashboardClient.get('/api/jobs', {
      params: agentId ? { agent_id: agentId } : {},
    })
    return response.data
  },

  // Job unique (pour le suivi de statut d'une restauration en cours)
  async getJob(jobId: number): Promise<Job> {
    const response = await dashboardClient.get(`/api/jobs/${jobId}`)
    return response.data
  },

  // Snapshots
  async getSnapshots(): Promise<Snapshot[]> {
    const response = await dashboardClient.get('/api/snapshots')
    return response.data
  },

  // Téléchargement d'agent
  async downloadAgent(platform: string): Promise<Blob> {
    const response = await apiClient.get(`/download/agent/${platform}`, {
      responseType: 'blob'
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
      verify_ssl: false
    }
  }
}

export { apiClient }