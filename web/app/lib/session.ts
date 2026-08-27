import { cookies } from 'next/headers'

// Cookie de session httpOnly (JWT utilisateur) : jamais exposé au JS
// navigateur, lu uniquement côté serveur par les routes proxy
// (web/app/api/**) — voir docs/adr/0005-gestion-utilisateurs-roles.md.
export const SESSION_COOKIE = 'saveos_session'

// En-tête Authorization à faire suivre vers l'API si une session existe ;
// {} sinon (repli sur le token dashboard statique déjà attaché par défaut
// à serverApi.defaults.headers, voir web/app/lib/serverApi.ts).
export function authHeaders(): { Authorization?: string } {
  const token = cookies().get(SESSION_COOKIE)?.value
  return token ? { Authorization: `Bearer ${token}` } : {}
}
