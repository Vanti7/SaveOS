import { NextResponse } from 'next/server'
import { serverApi } from '../../../lib/serverApi'
import { proxyErrorResponse } from '../../../lib/proxyError'
import { authHeaders } from '../../../lib/session'

export async function GET() {
  try {
    const response = await serverApi.get('/api/v1/auth/me', { headers: authHeaders() })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
