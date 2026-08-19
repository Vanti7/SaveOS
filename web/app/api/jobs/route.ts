import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../lib/serverApi'
import { proxyErrorResponse } from '../../lib/proxyError'

export async function GET(request: NextRequest) {
  const agentId = request.nextUrl.searchParams.get('agent_id')

  try {
    const response = await serverApi.get('/api/v1/jobs', {
      params: agentId ? { agent_id: agentId } : {},
    })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
