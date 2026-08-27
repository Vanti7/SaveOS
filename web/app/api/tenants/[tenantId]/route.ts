import { NextResponse } from 'next/server'
import { serverApi } from '../../../lib/serverApi'
import { proxyErrorResponse } from '../../../lib/proxyError'
import { authHeaders } from '../../../lib/session'

export async function GET(_request: Request, { params }: { params: { tenantId: string } }) {
  try {
    const response = await serverApi.get(`/api/v1/tenants/${params.tenantId}`, { headers: authHeaders() })
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
