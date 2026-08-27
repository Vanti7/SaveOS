import { NextRequest, NextResponse } from 'next/server'

// Cookie de session httpOnly, voir web/app/lib/session.ts (même nom,
// dupliqué ici volontairement : le Edge Runtime du middleware ne peut pas
// importer next/headers ni le reste de web/app/lib).
const SESSION_COOKIE = 'saveos_session'
const PUBLIC_PATHS = ['/login']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isPublic = PUBLIC_PATHS.some((path) => pathname.startsWith(path))
  const hasSession = request.cookies.has(SESSION_COOKIE)

  if (!isPublic && !hasSession) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  if (isPublic && hasSession) {
    return NextResponse.redirect(new URL('/', request.url))
  }
  return NextResponse.next()
}

export const config = {
  // Toutes les pages, hors routes API (auth gérée côté API/serverApi) et
  // assets statiques.
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
