import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../../lib/serverApi'
import { proxyErrorResponse } from '../../../lib/proxyError'
import { authHeaders } from '../../../lib/session'

export async function GET(_request: Request, { params }: { params: { agentId: string } }) {
  try {
    const response = await serverApi.get(`/api/v1/agents/${params.agentId}`, { headers: authHeaders() })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function PATCH(request: NextRequest, { params }: { params: { agentId: string } }) {
  try {
    const body = await request.json()
    const response = await serverApi.patch(`/api/v1/agents/${params.agentId}`, body, { headers: authHeaders() })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function DELETE(_request: Request, { params }: { params: { agentId: string } }) {
  try {
    await serverApi.delete(`/api/v1/agents/${params.agentId}`, { headers: authHeaders() })
    return new NextResponse(null, { status: 204 })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
