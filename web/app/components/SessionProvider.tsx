'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { api, User } from '../lib/api'

interface SessionContextValue {
  user: User | null
  loading: boolean
  logout: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    // Pas de session sur /login (middleware.ts garantit qu'on n'y arrive
    // jamais autrement) — inutile d'appeler l'API depuis cette page.
    if (pathname === '/login') {
      setLoading(false)
      return
    }
    api.getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [pathname])

  const logout = async () => {
    await api.logout()
    setUser(null)
    router.push('/login')
    router.refresh()
  }

  return (
    <SessionContext.Provider value={{ user, loading, logout }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSession doit être utilisé à l\'intérieur de <SessionProvider>')
  }
  return context
}
