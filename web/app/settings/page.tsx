'use client'

import { useState } from 'react'
import { SettingsIcon, SaveIcon, RefreshCwIcon, UsersIcon, PlusIcon, CopyIcon, CheckIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../lib/api'
import { useTenant } from '../components/TenantProvider'

function TenantsCard() {
  const { tenants, refreshTenants, loading } = useTenant()
  const [newTenantName, setNewTenantName] = useState('')
  const [creating, setCreating] = useState(false)
  const [newSecret, setNewSecret] = useState<{ name: string; secret: string } | null>(null)
  const [copied, setCopied] = useState(false)

  const handleCreate = async () => {
    if (!newTenantName.trim()) return
    try {
      setCreating(true)
      const tenant = await api.createTenant(newTenantName.trim())
      setNewSecret({ name: tenant.name, secret: tenant.registration_secret })
      setNewTenantName('')
      await refreshTenants()
      toast.success(`Tenant "${tenant.name}" créé`)
    } catch (error) {
      toast.error('Erreur lors de la création du tenant')
    } finally {
      setCreating(false)
    }
  }

  const copySecret = async () => {
    if (!newSecret) return
    try {
      await navigator.clipboard.writeText(newSecret.secret)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch (error) {
      toast.error('Erreur lors de la copie')
    }
  }

  return (
    <div className="card mt-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
        <UsersIcon className="w-5 h-5 mr-2" />
        Tenants
      </h2>

      {newSecret && (
        <div className="mb-6 p-4 bg-primary-50 rounded-lg">
          <p className="text-sm font-medium text-primary-900 mb-2">
            Secret d'enregistrement de "{newSecret.name}" — affiché une seule fois, à transmettre aux agents de ce tenant :
          </p>
          <div className="flex items-center justify-between bg-white rounded-lg p-3">
            <code className="text-xs text-gray-800 flex-1 mr-2 break-all">{newSecret.secret}</code>
            <button onClick={copySecret} className="text-gray-500 hover:text-gray-700 flex-shrink-0">
              {copied ? <CheckIcon className="w-4 h-4 text-green-500" /> : <CopyIcon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}

      <div className="flex items-end space-x-3 mb-6">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-2">Nouveau tenant</label>
          <input
            type="text"
            className="input-field"
            placeholder="Nom du tenant"
            value={newTenantName}
            onChange={(e) => setNewTenantName(e.target.value)}
          />
        </div>
        <button onClick={handleCreate} disabled={creating || !newTenantName.trim()} className="btn-primary flex items-center">
          <PlusIcon className="w-4 h-4 mr-2" />
          Créer
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Chargement...</p>
      ) : tenants.length === 0 ? (
        <p className="text-sm text-gray-500">Aucun tenant pour l'instant.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-200">
              <th className="pb-2">Nom</th>
              <th className="pb-2">Quota</th>
              <th className="pb-2">Créé le</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tenant) => (
              <tr key={tenant.id} className="border-b border-gray-100">
                <td className="py-2">{tenant.name}</td>
                <td className="py-2">{(tenant.quota_bytes / 1e9).toFixed(1)} GB</td>
                <td className="py-2">{new Date(tenant.created_at).toLocaleDateString('fr-FR')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    serverName: 'SaveOS Server',
    maxAgents: 100,
    defaultRetention: 30,
    backupSchedule: '0 2 * * *',
    alertEmail: 'admin@saveos.local',
    enableNotifications: true,
    enableMetrics: true,
    logLevel: 'INFO'
  })

  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    try {
      setSaving(true)
      // Simuler la sauvegarde
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success('Paramètres sauvegardés avec succès!')
    } catch (error) {
      toast.error('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (field: string, value: any) => {
    setSettings(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Paramètres système</h1>
        <p className="text-gray-600 mt-2">
          Configurez votre serveur SaveOS et ses fonctionnalités
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Paramètres généraux */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
            <SettingsIcon className="w-5 h-5 mr-2" />
            Paramètres généraux
          </h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nom du serveur
              </label>
              <input
                type="text"
                className="input-field"
                value={settings.serverName}
                onChange={(e) => handleInputChange('serverName', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nombre maximum d'agents
              </label>
              <input
                type="number"
                className="input-field"
                value={settings.maxAgents}
                onChange={(e) => handleInputChange('maxAgents', parseInt(e.target.value))}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rétention par défaut (jours)
              </label>
              <input
                type="number"
                className="input-field"
                value={settings.defaultRetention}
                onChange={(e) => handleInputChange('defaultRetention', parseInt(e.target.value))}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Planning de sauvegarde par défaut (cron)
              </label>
              <input
                type="text"
                className="input-field"
                value={settings.backupSchedule}
                onChange={(e) => handleInputChange('backupSchedule', e.target.value)}
                placeholder="0 2 * * *"
              />
              <p className="text-xs text-gray-500 mt-1">
                Format cron : minute heure jour mois jour_semaine
              </p>
            </div>
          </div>
        </div>

        {/* Notifications et alertes */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            Notifications et alertes
          </h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email d'alerte
              </label>
              <input
                type="email"
                className="input-field"
                value={settings.alertEmail}
                onChange={(e) => handleInputChange('alertEmail', e.target.value)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Notifications activées
                </label>
                <p className="text-xs text-gray-500">
                  Recevoir des notifications par email
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={settings.enableNotifications}
                  onChange={(e) => handleInputChange('enableNotifications', e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Métriques activées
                </label>
                <p className="text-xs text-gray-500">
                  Collecter les métriques système
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={settings.enableMetrics}
                  onChange={(e) => handleInputChange('enableMetrics', e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Niveau de log
              </label>
              <select
                className="input-field"
                value={settings.logLevel}
                onChange={(e) => handleInputChange('logLevel', e.target.value)}
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <TenantsCard />

      {/* Informations système */}
      <div className="card mt-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          Informations système
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900">Version</h3>
            <p className="text-2xl font-bold text-primary-600">1.0.0-MVP</p>
            <p className="text-sm text-gray-500">SaveOS Server</p>
          </div>
          
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900">Uptime</h3>
            <p className="text-2xl font-bold text-success-600">2h 15m</p>
            <p className="text-sm text-gray-500">Temps de fonctionnement</p>
          </div>
          
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900">Stockage</h3>
            <p className="text-2xl font-bold text-warning-600">45%</p>
            <p className="text-sm text-gray-500">Utilisation</p>
          </div>
        </div>

        <div className="mt-6 p-4 bg-primary-50 rounded-lg">
          <h4 className="text-sm font-medium text-primary-900 mb-2">
            URLs d'accès
          </h4>
          <div className="space-y-2 text-sm text-primary-700">
            <div className="flex justify-between">
              <span>Interface Web:</span>
              <code>http://localhost:3000</code>
            </div>
            <div className="flex justify-between">
              <span>API REST:</span>
              <code>https://localhost:8000</code>
            </div>
            <div className="flex justify-between">
              <span>MinIO Console:</span>
              <code>http://localhost:9001</code>
            </div>
          </div>
        </div>
      </div>

      {/* Boutons d'action */}
      <div className="flex justify-end space-x-4 mt-8">
        <button className="btn-secondary flex items-center">
          <RefreshCwIcon className="w-4 h-4 mr-2" />
          Réinitialiser
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center"
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Sauvegarde...
            </>
          ) : (
            <>
              <SaveIcon className="w-4 h-4 mr-2" />
              Sauvegarder
            </>
          )}
        </button>
      </div>
    </div>
  )
}