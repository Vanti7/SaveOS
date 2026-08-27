import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { TenantProvider, useTenant } from './TenantProvider'
import { api } from '../lib/api'

// Un utilisateur connecté est toujours limité à son propre tenant (voir
// docs/adr/0005-gestion-utilisateurs-roles.md) : GET /api/v1/tenants reste
// réservé au token dashboard statique, jamais utilisé depuis /login.
// TenantProvider ne doit donc jamais appeler getTenants() pour une session
// utilisateur — sinon chaque navigation déclenche un appel voué à l'échec
// (403), constaté en conditions réelles (dizaines d'appels répétés dans les
// logs de l'API après quelques clics dans le tableau de bord).
let mockUseSessionReturn: { user: any; loading: boolean }

vi.mock('./SessionProvider', () => ({
  useSession: () => mockUseSessionReturn,
}))

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}))

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return { ...actual, api: { ...actual.api, getTenants: vi.fn() } }
})

function Consumer() {
  const { tenants, loading } = useTenant()
  return <div data-testid="state">{loading ? 'loading' : `tenants:${tenants.length}`}</div>
}

describe('TenantProvider', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it("n'appelle jamais getTenants() pour une session utilisateur connectée", async () => {
    mockUseSessionReturn = { user: { id: 1, email: 'a@test.local', role: 'admin', tenant_id: 1 }, loading: false }
    vi.mocked(api.getTenants).mockResolvedValue([{ id: 1, name: 'x', quota_bytes: 1, retention_policy: '{}', created_at: '' }])

    render(
      <TenantProvider>
        <Consumer />
      </TenantProvider>
    )

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('tenants:0'))
    expect(api.getTenants).not.toHaveBeenCalled()
  })

  it('attend la résolution de la session avant de décider (pas de double appel)', async () => {
    mockUseSessionReturn = { user: null, loading: true }
    vi.mocked(api.getTenants).mockResolvedValue([])

    render(
      <TenantProvider>
        <Consumer />
      </TenantProvider>
    )

    expect(screen.getByTestId('state')).toHaveTextContent('loading')
    expect(api.getTenants).not.toHaveBeenCalled()
  })

  it("appelle getTenants() en l'absence de session utilisateur (token dashboard statique)", async () => {
    mockUseSessionReturn = { user: null, loading: false }
    vi.mocked(api.getTenants).mockResolvedValue([
      { id: 1, name: 'tenant-a', quota_bytes: 1, retention_policy: '{}', created_at: '' },
    ])

    render(
      <TenantProvider>
        <Consumer />
      </TenantProvider>
    )

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('tenants:1'))
    expect(api.getTenants).toHaveBeenCalledTimes(1)
  })
})
