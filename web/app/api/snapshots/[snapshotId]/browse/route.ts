import { NextRequest, NextResponse } from 'next/server'
import { serverApi } from '../../../../lib/serverApi'
import { proxyErrorResponse } from '../../../../lib/proxyError'

export async function POST(request: NextRequest, { params }: { params: { snapshotId: string } }) {
  const body = await request.json()
  const { agent_id, ...rest } = body

  try {
    const response = await serverApi.post(
      `/api/v1/backup/${agent_id}/snapshots/${params.snapshotId}/browse`,
      rest,
    )
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
