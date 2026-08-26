import { describe, it, expect, afterEach, vi } from 'vitest'

// api.ts lit process.env.NEXT_PUBLIC_API_URL au chargement du module : on
// doit stub l'env puis réimporter à chaud (vi.resetModules) pour chaque cas.
describe('httpsAgent.rejectUnauthorized (docs/adr/0003-certificats-tls-production.md)', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('désactive la vérification TLS pour localhost (self-signed dev)', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://localhost:8000')
    const { apiClient } = await import('./api')
    expect((apiClient.defaults.httpsAgent as any).options.rejectUnauthorized).toBe(false)
  })

  it('active la vérification TLS pour un domaine public (certificat Let\'s Encrypt valide)', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.saveos.com')
    const { apiClient } = await import('./api')
    expect((apiClient.defaults.httpsAgent as any).options.rejectUnauthorized).toBe(true)
  })
})
