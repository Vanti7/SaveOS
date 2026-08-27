'use client'

import { useState } from 'react'
import { DownloadIcon, CopyIcon, CheckIcon, ServerIcon, PackageIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import fileDownload from 'js-file-download'
import { api } from '../lib/api'
import { useTenant } from '../components/TenantProvider'
import { useSession } from '../components/SessionProvider'

interface PlatformInfo {
  id: string
  name: string
  icon: string
  description: string
  requirements: string[]
  installCommand: string
  downloadUrl: string
}

const platforms: PlatformInfo[] = [
  {
    id: 'windows',
    name: 'Windows',
    icon: '🪟',
    description: 'Agent pour Windows 10/11 (x64)',
    requirements: [
      'Windows 10 ou supérieur',
      'Python 3.8+ (installé automatiquement)',
      'Droits administrateur pour l\'installation'
    ],
    installCommand: 'powershell -ExecutionPolicy Bypass -File install-saveos-agent.ps1',
    downloadUrl: '/api/download/agent/windows'
  },
  {
    id: 'macos',
    name: 'macOS',
    icon: '🍎',
    description: 'Agent pour macOS (Intel & Apple Silicon)',
    requirements: [
      'macOS 10.15 (Catalina) ou supérieur',
      'Homebrew (recommandé)',
      'Accès administrateur'
    ],
    installCommand: 'bash install-saveos-agent.sh',
    downloadUrl: '/api/download/agent/macos'
  },
  {
    id: 'linux',
    name: 'Linux',
    icon: '🐧',
    description: 'Agent pour distributions Linux (x64)',
    requirements: [
      'Ubuntu 18.04+ / CentOS 7+ / Debian 10+',
      'Python 3.8+',
      'Accès sudo'
    ],
    installCommand: 'sudo bash install-saveos-agent.sh',
    downloadUrl: '/api/download/agent/linux'
  }
]

export default function DownloadsPage() {
  const [selectedPlatform, setSelectedPlatform] = useState<string>('')
  const [copying, setCopying] = useState<string>('')
  const [downloading, setDownloading] = useState<string>('')
  const [configData, setConfigData] = useState<any>(null)
  const { selectedTenantId } = useTenant()
  const { user } = useSession()
  // Un utilisateur connecté (admin/user) est toujours limité à son propre
  // tenant (voir docs/adr/0005-gestion-utilisateurs-roles.md) — le
  // sélecteur de la barre latérale ne s'affiche plus pour lui (il n'a
  // qu'un seul tenant), donc son tenant vient de sa session, pas du
  // sélecteur (pertinent seulement pour une session au token dashboard
  // statique, jamais utilisée depuis /login).
  const effectiveTenantId = user?.tenant_id ?? selectedTenantId

  const generateAgentPackage = async (platform: string) => {
    if (effectiveTenantId === null || effectiveTenantId === undefined) {
      toast.error('Sélectionnez un tenant avant de provisionner un agent')
      return
    }

    try {
      setDownloading(platform)

      // Demander le hostname à l'utilisateur
      const hostname = prompt('Nom de la machine (hostname):') || `${platform}-agent-${Date.now()}`

      // Provisionne l'agent sur le serveur (token dédié), puis télécharge
      // le package source pré-configuré avec CE hostname et CE token : le
      // script d'installation embarqué s'y connecte directement, sans
      // appel réseau supplémentaire ni secret à ressaisir — voir
      // docs/adr/0007-provisioning-package-source.md (voir aussi
      // web/app/lib/api.ts pour l'installeur natif exe/dmg/deb, qui ne
      // nécessite pas ce provisioning).
      const provisionData = await api.provisionAgent(hostname, platform, effectiveTenantId)
      setConfigData(provisionData)

      const blob = await api.downloadAgent(platform, {
        hostname: provisionData.hostname,
        token: provisionData.token,
      })
      const filename = `saveos-agent-${hostname}-${platform}.${platform === 'windows' ? 'zip' : 'tar.gz'}`
      fileDownload(blob, filename)

      toast.success(`Package ${platform} téléchargé avec succès!`)
      toast.success(`Agent provisionné: ${hostname}`)

    } catch (error) {
      console.error('Erreur lors du téléchargement:', error)
      toast.error('Erreur lors de la génération du package')
    } finally {
      setDownloading('')
    }
  }



  const copyToClipboard = async (text: string, id: string) => {
    try {
      setCopying(id)
      await navigator.clipboard.writeText(text)
      toast.success('Commande copiée!')
      setTimeout(() => setCopying(''), 1000)
    } catch (error) {
      toast.error('Erreur lors de la copie')
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Télécharger les agents</h1>
        <p className="text-gray-600 mt-2">
          Téléchargez et installez l'agent SaveOS sur vos machines
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {platforms.map((platform) => (
          <div key={platform.id} className="card">
            <div className="text-center mb-6">
              <div className="text-4xl mb-3">{platform.icon}</div>
              <h3 className="text-xl font-semibold text-gray-900">{platform.name}</h3>
              <p className="text-sm text-gray-600 mt-1">{platform.description}</p>
            </div>

            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Prérequis :</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                {platform.requirements.map((req, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-primary-500 mr-2">•</span>
                    {req}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Installation :</h4>
              <div className="bg-gray-100 rounded-lg p-3 flex items-center justify-between">
                <code className="text-xs text-gray-800 flex-1 mr-2">
                  {platform.installCommand}
                </code>
                <button
                  onClick={() => copyToClipboard(platform.installCommand, platform.id)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  {copying === platform.id ? (
                    <CheckIcon className="w-4 h-4 text-green-500" />
                  ) : (
                    <CopyIcon className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <p className="text-xs text-gray-500 mb-2">
              Le package source nécessite Python ; l'installeur natif est autonome
              et enregistre le service au démarrage automatiquement.
            </p>

            <button
              onClick={() => generateAgentPackage(platform.id)}
              disabled={downloading === platform.id}
              className="btn-primary w-full flex items-center justify-center"
            >
              {downloading === platform.id ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Génération...
                </>
              ) : (
                <>
                  <DownloadIcon className="w-4 h-4 mr-2" />
                  Package source (.{platform.id === 'windows' ? 'zip' : 'tar.gz'})
                </>
              )}
            </button>

            <a
              href={api.installerDownloadUrl(platform.id)}
              className="btn-secondary w-full flex items-center justify-center mt-3"
            >
              <PackageIcon className="w-4 h-4 mr-2" />
              Installeur natif ({platform.id === 'windows' ? '.exe' : platform.id === 'macos' ? '.dmg' : '.deb'})
            </a>
          </div>
        ))}
      </div>

      {/* Instructions détaillées */}
      <div className="mt-12 card">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Instructions d'installation
        </h2>
        
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              1. Téléchargement du package
            </h3>
            <p className="text-gray-600">
              Cliquez sur "Télécharger" pour la plateforme souhaitée. Un package d'installation 
              personnalisé sera généré avec la configuration pré-remplie pour votre serveur SaveOS.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              2. Installation sur la machine cible
            </h3>
            <p className="text-gray-600">
              Transférez le package téléchargé sur la machine à sauvegarder et exécutez 
              le script d'installation. L'agent s'enregistrera automatiquement auprès du serveur.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              3. Vérification
            </h3>
            <p className="text-gray-600">
              Une fois installé, l'agent apparaîtra dans la liste des agents et commencera 
              à envoyer des heartbeats. Vous pourrez alors configurer les sauvegardes.
            </p>
          </div>
        </div>

        <div className="mt-8 p-4 bg-primary-50 rounded-lg">
          <div className="flex items-start">
            <ServerIcon className="w-5 h-5 text-primary-600 mt-0.5 mr-3" />
            <div>
              <h4 className="text-sm font-medium text-primary-900">
                Connexion automatique au serveur
              </h4>
              <p className="text-sm text-primary-700 mt-1">
                Chaque package téléchargé est pré-configuré pour se connecter automatiquement 
                à ce serveur SaveOS. Cela garantit que l'agent pourra communiquer avec le serveur 
                dès l'installation.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}