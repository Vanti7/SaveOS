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

// provisionAgent exigeait autrefois aucune authentification et appelait
// l'API distante directement depuis le navigateur (/api/v1/agents/provision).
// Le provisioning exige désormais le token dashboard (jamais accessible côté
// client) : l'appel doit passer par la route proxy Next.js relative
// (/api/agents/provision), voir docs/adr/0004-multi-tenancy-avancee.md.
describe('api.provisionAgent', () => {
  afterEach(() => {
    vi.doUnmock('axios')
    vi.resetModules()
  })

  it('appelle la route proxy relative, jamais l\'API distante directement', async () => {
    const postMock = vi.fn().mockResolvedValue({ data: { agent_id: 1, token: 'tok' } })
    vi.doMock('axios', () => ({
      default: {
        create: vi.fn(() => ({ get: vi.fn(), post: postMock, defaults: {} })),
      },
    }))

    const { api } = await import('./api')
    await api.provisionAgent('host', 'linux', 42)

    expect(postMock).toHaveBeenCalledWith(
      '/api/agents/provision',
      null,
      { params: { hostname: 'host', platform: 'linux', tenant_id: 42 } }
    )
  })
})
