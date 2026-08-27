import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../lib/serverApi'
import { proxyErrorResponse } from '../../lib/proxyError'
import { authHeaders } from '../../lib/session'

export async function GET(request: NextRequest) {
  const tenantId = request.nextUrl.searchParams.get('tenant_id')

  try {
    const response = await serverApi.get('/api/v1/agents', {
      params: tenantId ? { tenant_id: tenantId } : {},
      headers: authHeaders(),
    })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
