import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../lib/serverApi'
import { proxyErrorResponse } from '../../lib/proxyError'

export async function GET() {
  try {
    const response = await serverApi.get('/api/v1/tenants')
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json()

  try {
    const response = await serverApi.post('/api/v1/tenants', body)
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
