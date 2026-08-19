import axios from 'axios'
import https from 'https'

// Client server-only : ne jamais importer ce fichier depuis un composant
// 'use client' (le token dashboard ne doit jamais atteindre le navigateur).
const API_URL = process.env.API_URL || 'https://api:8000'
const DASHBOARD_API_TOKEN = process.env.DASHBOARD_API_TOKEN || ''

const serverApi = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    ...(DASHBOARD_API_TOKEN ? { Authorization: `Bearer ${DASHBOARD_API_TOKEN}` } : {}),
  },
})

// Pour le MVP, on désactive la vérification SSL (certificat self-signed),
// comme web/app/lib/api.ts.
serverApi.defaults.httpsAgent = new https.Agent({ rejectUnauthorized: false })

export { serverApi }
