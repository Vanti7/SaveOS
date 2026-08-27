import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../lib/serverApi'
import { proxyErrorResponse } from '../../lib/proxyError'
import { authHeaders } from '../../lib/session'

export async function GET() {
  try {
    const response = await serverApi.get('/api/v1/users', { headers: authHeaders() })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json()

  try {
    const response = await serverApi.post('/api/v1/users', body, { headers: authHeaders() })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
