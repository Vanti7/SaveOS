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
    // Pour le MVP, on retourne des données simulées
    // Dans une vraie implémentation, on ferait appel à l'API
    return [
      {
        id: 1,
        hostname: 'DESKTOP-ABC123',
        platform: 'windows',
        status: 'active',
        last_seen: new Date().toISOString(),
        created_at: new Date(Date.now() - 86400000).toISOString()
      },
      {
        id: 2,
        hostname: 'MacBook-Pro',
        platform: 'darwin',
        status: 'active',
        last_seen: new Date(Date.now() - 3600000).toISOString(),
        created_at: new Date(Date.now() - 172800000).toISOString()
      },
      {
        id: 3,
        hostname: 'Ubuntu-Server',
        platform: 'linux',
        status: 'error',
        last_seen: new Date(Date.now() - 7200000).toISOString(),
        created_at: new Date(Date.now() - 259200000).toISOString()
      }
    ]
  },

  // Jobs
  async getJobs(): Promise<Job[]> {
    return [
      {
        id: 1,
        agent_id: 1,
        type: 'backup',
        status: 'completed',
        started_at: new Date(Date.now() - 3600000).toISOString(),
        finished_at: new Date(Date.now() - 1800000).toISOString(),
        created_at: new Date(Date.now() - 3600000).toISOString()
      },
      {
        id: 2,
        agent_id: 2,
        type: 'backup',
        status: 'running',
        started_at: new Date(Date.now() - 600000).toISOString(),
        created_at: new Date(Date.now() - 600000).toISOString()
      }
    ]
  },

  // Snapshots
  async getSnapshots(): Promise<Snapshot[]> {
    return [
      {
        id: 1,
        job_id: 1,
        name: 'DESKTOP-ABC123_20231215_140000',
        repo_path: '/tmp/borg_repos/DESKTOP-ABC123',
        size_bytes: 1024 * 1024 * 512, // 512MB
        is_full: true,
        created_at: new Date(Date.now() - 1800000).toISOString()
      }
    ]
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