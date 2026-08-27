import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { serverApi } from '../../../lib/serverApi'
import { proxyErrorResponse } from '../../../lib/proxyError'
import { SESSION_COOKIE } from '../../../lib/session'

export async function POST(request: NextRequest) {
  const body = await request.json()

  try {
    const response = await serverApi.post('/api/v1/auth/login', body)
    const { access_token, user } = response.data

    cookies().set(SESSION_COOKIE, access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24, // 24h, aligné sur le défaut JWT_EXPIRE_MINUTES côté API
      path: '/',
    })

    return NextResponse.json({ user })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
