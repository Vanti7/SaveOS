import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RestoreModal from './RestoreModal'
import { api, Snapshot } from '../lib/api'

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return {
    ...actual,
    api: {
      browseSnapshot: vi.fn(),
      createRestoreJob: vi.fn(),
      getJob: vi.fn(),
      downloadRestorePackage: vi.fn(),
    },
  }
})

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

const snapshot: Snapshot = {
  id: 2,
  job_id: 6,
  agent_id: 1,
  name: 'DESKTOP-TEST_20260101_000000',
  repo_path: '/tmp/borg_repos/DESKTOP-TEST',
  size_bytes: 1024,
  is_full: true,
  created_at: new Date().toISOString(),
}

describe('RestoreModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('browses the snapshot root on mount', async () => {
    vi.mocked(api.browseSnapshot).mockResolvedValue({
      path: '',
      entries: [{ path: 'app', type: 'd', size: undefined, mtime: undefined }],
    })

    render(<RestoreModal snapshot={snapshot} onClose={vi.fn()} />)

    expect(api.browseSnapshot).toHaveBeenCalledWith(2, 1, '')
    expect(await screen.findByText('app')).toBeInTheDocument()
  })

  it('navigates into a directory and re-browses with the new path', async () => {
    vi.mocked(api.browseSnapshot).mockImplementation(async (_id, _agentId, path) => {
      if (!path) return { path: '', entries: [{ path: 'app', type: 'd' }] }
      return { path: 'app', entries: [{ path: 'app/file.txt', type: '-', size: 42 }] }
    })

    render(<RestoreModal snapshot={snapshot} onClose={vi.fn()} />)

    const dirButton = await screen.findByText('app')
    await userEvent.click(dirButton)

    expect(await screen.findByText('file.txt')).toBeInTheDocument()
    expect(api.browseSnapshot).toHaveBeenCalledWith(2, 1, 'app')
  })

  it('disables "Suivant" until at least one entry is selected, then advances to the target step', async () => {
    vi.mocked(api.browseSnapshot).mockResolvedValue({
      path: '',
      entries: [{ path: 'file.txt', type: '-', size: 10 }],
    })

    render(<RestoreModal snapshot={snapshot} onClose={vi.fn()} />)

    const nextButton = await screen.findByRole('button', { name: /suivant/i })
    expect(nextButton).toBeDisabled()

    const checkbox = await screen.findByRole('checkbox')
    await userEvent.click(checkbox)
    expect(nextButton).toBeEnabled()

    await userEvent.click(nextButton)
    expect(screen.getByText(/1 élément\(s\) sélectionné\(s\)/)).toBeInTheDocument()
  })

  it('creates a download restore job and shows the download button once completed', async () => {
    vi.mocked(api.browseSnapshot).mockResolvedValue({
      path: '',
      entries: [{ path: 'file.txt', type: '-', size: 10 }],
    })
    vi.mocked(api.createRestoreJob).mockResolvedValue({
      id: 42,
      agent_id: 1,
      type: 'restore',
      status: 'completed',
      created_at: new Date().toISOString(),
    })

    render(<RestoreModal snapshot={snapshot} onClose={vi.fn()} />)

    await userEvent.click(await screen.findByRole('checkbox'))
    await userEvent.click(screen.getByRole('button', { name: /suivant/i }))
    await userEvent.click(screen.getByRole('button', { name: /lancer la restauration/i }))

    expect(api.createRestoreJob).toHaveBeenCalledWith({
      agent_id: 1,
      snapshot_id: 2,
      selected_paths: ['file.txt'],
      target: 'download',
      restore_path: undefined,
    })

    const downloadButton = await screen.findByRole('button', { name: /télécharger le paquet/i })
    await userEvent.click(downloadButton)
    expect(api.downloadRestorePackage).toHaveBeenCalledWith(42, 'restore_42.zip')
  })

  it('calls onClose when the close button is clicked', async () => {
    vi.mocked(api.browseSnapshot).mockResolvedValue({ path: '', entries: [] })
    const onClose = vi.fn()

    render(<RestoreModal snapshot={snapshot} onClose={onClose} />)

    const closeButtons = await screen.findAllByRole('button')
    const xButton = closeButtons[0]
    await userEvent.click(xButton)

    expect(onClose).toHaveBeenCalled()
  })
})
