import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../../lib/serverApi'
import { proxyErrorResponse } from '../../../lib/proxyError'

// hostname/platform/tenant_id sont des query params côté API (pas un body
// JSON) — voir api/main.py::provision_agent.
export async function POST(request: NextRequest) {
  const hostname = request.nextUrl.searchParams.get('hostname')
  const platform = request.nextUrl.searchParams.get('platform')
  const tenantId = request.nextUrl.searchParams.get('tenant_id')

  try {
    const response = await serverApi.post('/api/v1/agents/provision', null, {
      params: { hostname, platform, tenant_id: tenantId },
    })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
