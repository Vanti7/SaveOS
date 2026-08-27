'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { api, Tenant } from '../lib/api'
import { useSession } from './SessionProvider'

const STORAGE_KEY = 'saveos_selected_tenant_id'

interface TenantContextValue {
  tenants: Tenant[]
  selectedTenantId: number | null
  setSelectedTenantId: (id: number | null) => void
  loading: boolean
  refreshTenants: () => Promise<void>
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined)

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selectedTenantId, setSelectedTenantIdState] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const pathname = usePathname()
  const { user, loading: sessionLoading } = useSession()

  const refreshTenants = async () => {
    try {
      const data = await api.getTenants()
      setTenants(data)
    } catch (error) {
      console.error('Erreur lors du chargement des tenants:', error)
    }
  }

  useEffect(() => {
    // Pas de session sur /login (middleware.ts garantit qu'on n'y arrive
    // jamais autrement) — inutile d'appeler l'API depuis cette page.
    if (pathname === '/login') {
      setLoading(false)
      return
    }
    // Attend que useSession() ait résolu avant de décider s'il faut appeler
    // l'API, plutôt que de tenter un premier appel voué à l'échec puis un
    // second correct juste après.
    if (sessionLoading) {
      return
    }
    if (user) {
      // Un utilisateur connecté est toujours limité à son propre tenant et
      // ne peut jamais lister tous les tenants (réservé au token dashboard
      // statique, jamais utilisé depuis /login — voir
      // docs/adr/0005-gestion-utilisateurs-roles.md) : appeler l'API
      // échouerait systématiquement (403) à chaque navigation, pour rien.
      setTenants([])
      setLoading(false)
      return
    }
    // null = "tous les tenants" (vue super-admin) — pas d'erreur si absent
    // ou invalide, on retombe simplement sur ce défaut.
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) setSelectedTenantIdState(Number(stored))
    } catch {
      // localStorage indisponible (navigation privée, etc.) : défaut "tous les tenants"
    }
    refreshTenants().finally(() => setLoading(false))
  }, [pathname, user, sessionLoading])

  const setSelectedTenantId = (id: number | null) => {
    setSelectedTenantIdState(id)
    try {
      if (id === null) {
        localStorage.removeItem(STORAGE_KEY)
      } else {
        localStorage.setItem(STORAGE_KEY, String(id))
      }
    } catch {
      // per-viewer convenience uniquement : une écriture échouée ne doit pas bloquer la sélection
    }
  }

  return (
    <TenantContext.Provider value={{ tenants, selectedTenantId, setSelectedTenantId, loading, refreshTenants }}>
      {children}
    </TenantContext.Provider>
  )
}

export function useTenant(): TenantContextValue {
  const context = useContext(TenantContext)
  if (!context) {
    throw new Error('useTenant doit être utilisé à l\'intérieur de <TenantProvider>')
  }
  return context
}
