'use client'

import { useEffect, useRef, useState } from 'react'
import {
  XIcon, FolderIcon, FileIcon, ChevronRightIcon, DownloadIcon,
  CheckCircleIcon, AlertTriangleIcon, Loader2Icon,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api, ArchiveEntry, Job, RestoreTarget, Snapshot } from '../lib/api'

interface RestoreModalProps {
  snapshot: Snapshot
  onClose: () => void
}

type Step = 'browse' | 'target' | 'progress'

const POLL_INTERVAL_MS = 3000

export default function RestoreModal({ snapshot, onClose }: RestoreModalProps) {
  const [step, setStep] = useState<Step>('browse')
  const [currentPath, setCurrentPath] = useState('')
  const [entries, setEntries] = useState<ArchiveEntry[]>([])
  const [loadingEntries, setLoadingEntries] = useState(true)
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())

  const [target, setTarget] = useState<RestoreTarget>('download')
  const [restorePath, setRestorePath] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [job, setJob] = useState<Job | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (step !== 'browse') return
    let cancelled = false
    setLoadingEntries(true)
    api.browseSnapshot(snapshot.id, snapshot.agent_id, currentPath)
      .then((res) => {
        if (!cancelled) setEntries(res.entries)
      })
      .catch(() => {
        if (!cancelled) toast.error('Erreur lors de la navigation dans le snapshot')
      })
      .finally(() => {
        if (!cancelled) setLoadingEntries(false)
      })
    return () => { cancelled = true }
  }, [step, currentPath, snapshot.id, snapshot.agent_id])

  useEffect(() => {
    if (step !== 'progress' || !job) return
    if (job.status === 'completed' || job.status === 'failed') return

    pollRef.current = setInterval(async () => {
      try {
        const updated = await api.getJob(job.id)
        setJob(updated)
      } catch {
        // on ignore une erreur de poll isolée, on retente au cycle suivant
      }
    }, POLL_INTERVAL_MS)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [step, job])

  const toggleSelected = (path: string) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const breadcrumbSegments = currentPath ? currentPath.split('/') : []

  const navigateTo = (index: number) => {
    setCurrentPath(breadcrumbSegments.slice(0, index + 1).join('/'))
  }

  const handleSubmitRestore = async () => {
    if (target === 'agent' && !restorePath.trim()) {
      toast.error("Le chemin de destination sur l'agent est requis")
      return
    }

    setSubmitting(true)
    try {
      const createdJob = await api.createRestoreJob({
        agent_id: snapshot.agent_id,
        snapshot_id: snapshot.id,
        selected_paths: Array.from(selectedPaths),
        target,
        restore_path: target === 'agent' ? restorePath.trim() : undefined,
      })
      setJob(createdJob)
      setStep('progress')
    } catch (error) {
      toast.error('Erreur lors de la création de la restauration')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDownload = async () => {
    if (!job) return
    try {
      await api.downloadRestorePackage(job.id, `restore_${job.id}.zip`)
    } catch {
      toast.error('Erreur lors du téléchargement')
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Restaurer</h2>
            <p className="text-sm text-gray-500">{snapshot.name}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {step === 'browse' && (
            <>
              <div className="flex items-center flex-wrap gap-1 text-sm text-gray-500 mb-3">
                <button className="hover:text-primary-600" onClick={() => setCurrentPath('')}>
                  racine
                </button>
                {breadcrumbSegments.map((segment, index) => (
                  <span key={index} className="flex items-center gap-1">
                    <ChevronRightIcon className="w-3 h-3" />
                    <button className="hover:text-primary-600" onClick={() => navigateTo(index)}>
                      {segment}
                    </button>
                  </span>
                ))}
              </div>

              {loadingEntries ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2Icon className="w-6 h-6 animate-spin text-primary-600" />
                </div>
              ) : entries.length === 0 ? (
                <p className="text-sm text-gray-500 py-8 text-center">Dossier vide</p>
              ) : (
                <ul className="divide-y divide-gray-100 border border-gray-200 rounded-md">
                  {entries.map((entry) => (
                    <li key={entry.path} className="flex items-center px-3 py-2 hover:bg-gray-50">
                      <input
                        type="checkbox"
                        className="mr-3"
                        checked={selectedPaths.has(entry.path)}
                        onChange={() => toggleSelected(entry.path)}
                      />
                      {entry.type === 'd' ? (
                        <FolderIcon className="w-4 h-4 text-primary-500 mr-2 shrink-0" />
                      ) : (
                        <FileIcon className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
                      )}
                      {entry.type === 'd' ? (
                        <button
                          className="text-sm text-gray-900 hover:text-primary-600 flex-1 text-left"
                          onClick={() => setCurrentPath(entry.path)}
                        >
                          {entry.path.split('/').pop()}
                        </button>
                      ) : (
                        <span className="text-sm text-gray-900 flex-1">{entry.path.split('/').pop()}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {step === 'target' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                {selectedPaths.size} élément(s) sélectionné(s)
              </p>

              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="target"
                    checked={target === 'download'}
                    onChange={() => setTarget('download')}
                  />
                  <span className="text-sm text-gray-900">Télécharger depuis le navigateur</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="target"
                    checked={target === 'agent'}
                    onChange={() => setTarget('agent')}
                  />
                  <span className="text-sm text-gray-900">Restaurer directement sur la machine agent</span>
                </label>
              </div>

              {target === 'agent' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Chemin de destination sur l'agent
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="/home/user/restore"
                    value={restorePath}
                    onChange={(e) => setRestorePath(e.target.value)}
                  />
                </div>
              )}
            </div>
          )}

          {step === 'progress' && job && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              {job.status === 'failed' ? (
                <>
                  <AlertTriangleIcon className="w-10 h-10 text-error-500 mb-3" />
                  <p className="text-sm font-medium text-gray-900">Échec de la restauration</p>
                  {job.error_message && (
                    <p className="text-sm text-gray-500 mt-1">{job.error_message}</p>
                  )}
                </>
              ) : job.status === 'completed' && target === 'download' ? (
                <>
                  <CheckCircleIcon className="w-10 h-10 text-success-500 mb-3" />
                  <p className="text-sm font-medium text-gray-900 mb-4">Paquet prêt</p>
                  <button onClick={handleDownload} className="btn-success flex items-center">
                    <DownloadIcon className="w-4 h-4 mr-2" />
                    Télécharger le paquet
                  </button>
                </>
              ) : job.status === 'completed' ? (
                <>
                  <CheckCircleIcon className="w-10 h-10 text-success-500 mb-3" />
                  <p className="text-sm font-medium text-gray-900">Restauration appliquée sur l'agent</p>
                </>
              ) : job.status === 'ready_for_agent' ? (
                <>
                  <Loader2Icon className="w-8 h-8 animate-spin text-primary-600 mb-3" />
                  <p className="text-sm font-medium text-gray-900">En attente de récupération par l'agent</p>
                  <p className="text-sm text-gray-500 mt-1">
                    L'agent applique la restauration à son prochain cycle
                  </p>
                </>
              ) : (
                <>
                  <Loader2Icon className="w-8 h-8 animate-spin text-primary-600 mb-3" />
                  <p className="text-sm font-medium text-gray-900">Extraction en cours...</p>
                </>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
          {step === 'browse' && (
            <>
              <button onClick={onClose} className="btn-secondary">Annuler</button>
              <button
                onClick={() => setStep('target')}
                disabled={selectedPaths.size === 0}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Suivant ({selectedPaths.size})
              </button>
            </>
          )}
          {step === 'target' && (
            <>
              <button onClick={() => setStep('browse')} className="btn-secondary">Retour</button>
              <button
                onClick={handleSubmitRestore}
                disabled={submitting}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Lancement...' : 'Lancer la restauration'}
              </button>
            </>
          )}
          {step === 'progress' && (
            <button onClick={onClose} className="btn-secondary">Fermer</button>
          )}
        </div>
      </div>
    </div>
  )
}
