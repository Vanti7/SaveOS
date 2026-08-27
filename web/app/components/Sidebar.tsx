'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  HomeIcon,
  ServerIcon,
  CameraIcon,
  DownloadIcon,
  SettingsIcon,
  ActivityIcon,
  LogOutIcon
} from 'lucide-react'
import { useTenant } from './TenantProvider'
import { useSession } from './SessionProvider'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Agents', href: '/agents', icon: ServerIcon },
  { name: 'Snapshots', href: '/snapshots', icon: CameraIcon },
  { name: 'Téléchargements', href: '/downloads', icon: DownloadIcon },
  { name: 'Monitoring', href: '/monitoring', icon: ActivityIcon },
  { name: 'Paramètres', href: '/settings', icon: SettingsIcon },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { tenants, selectedTenantId, setSelectedTenantId, loading: tenantsLoading } = useTenant()
  const { user, logout } = useSession()

  return (
    <div className="flex flex-col w-64 bg-white shadow-lg">
      <div className="flex items-center justify-center h-16 bg-primary-600">
        <h1 className="text-xl font-bold text-white">SaveOS</h1>
      </div>

      {/* Un utilisateur connecté est toujours limité à son propre tenant
          (voir docs/adr/0005-gestion-utilisateurs-roles.md) : ce sélecteur
          n'a de sens que pour une session au token dashboard statique
          (jamais utilisée depuis /login), donc seulement si getTenants()
          a réellement renvoyé plusieurs tenants. */}
      {!tenantsLoading && tenants.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-200">
          <label className="block text-xs font-medium text-gray-500 mb-1">Tenant</label>
          <select
            className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 bg-white"
            value={selectedTenantId ?? ''}
            onChange={(e) => setSelectedTenantId(e.target.value === '' ? null : Number(e.target.value))}
          >
            <option value="">Tous les tenants</option>
            {tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
            ))}
          </select>
        </div>
      )}

      <nav className="flex-1 px-4 py-6 space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors duration-200 ${
                isActive
                  ? 'bg-primary-100 text-primary-700 border-r-2 border-primary-600'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center min-w-0">
            <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-sm font-medium text-white">{user?.email?.[0]?.toUpperCase() ?? '?'}</span>
            </div>
            <div className="ml-3 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{user?.email ?? 'Chargement...'}</p>
              <p className="text-xs text-gray-500">{user?.role === 'admin' ? 'Administrateur' : user?.role === 'user' ? 'Utilisateur' : ''}</p>
            </div>
          </div>
          {user && (
            <button
              onClick={logout}
              title="Déconnexion"
              className="text-gray-400 hover:text-gray-600 flex-shrink-0 ml-2"
            >
              <LogOutIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}