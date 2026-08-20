import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SnapshotsPage from './page'
import { api } from '../lib/api'

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return { ...actual, api: { ...actual.api, getSnapshots: vi.fn() } }
})

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('../components/RestoreModal', () => ({
  default: ({ snapshot, onClose }: any) => (
    <div data-testid="restore-modal">
      Modal pour {snapshot.name}
      <button onClick={onClose}>Fermer la modale</button>
    </div>
  ),
}))

const snapshots = [
  {
    id: 1,
    job_id: 5,
    agent_id: 1,
    name: 'DESKTOP-TEST_20260101_000000',
    repo_path: '/tmp/borg_repos/DESKTOP-TEST',
    size_bytes: 1024 * 1024 * 512,
    is_full: true,
    created_at: new Date().toISOString(),
  },
]

describe('SnapshotsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the snapshot list with formatted size once loaded', async () => {
    vi.mocked(api.getSnapshots).mockResolvedValue(snapshots)

    render(<SnapshotsPage />)

    expect(await screen.findByText('DESKTOP-TEST_20260101_000000')).toBeInTheDocument()
    // "512 MB" apparaît à la fois dans la carte "Taille totale" et la ligne du tableau
    expect(screen.getAllByText('512 MB').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Complète')).toBeInTheDocument()
  })

  it('shows an empty state when there are no snapshots', async () => {
    vi.mocked(api.getSnapshots).mockResolvedValue([])

    render(<SnapshotsPage />)

    expect(await screen.findByText('Aucun snapshot trouvé')).toBeInTheDocument()
  })

  it('opens the restore modal for a snapshot when "Restaurer" is clicked', async () => {
    vi.mocked(api.getSnapshots).mockResolvedValue(snapshots)

    render(<SnapshotsPage />)

    await screen.findByText('DESKTOP-TEST_20260101_000000')
    await userEvent.click(screen.getByText('Restaurer'))

    expect(await screen.findByTestId('restore-modal')).toBeInTheDocument()
    expect(screen.getByText(/Modal pour DESKTOP-TEST_20260101_000000/)).toBeInTheDocument()

    await userEvent.click(screen.getByText('Fermer la modale'))
    expect(screen.queryByTestId('restore-modal')).not.toBeInTheDocument()
  })
})
