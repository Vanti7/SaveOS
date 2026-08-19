import { NextResponse } from 'next/server'
import { serverApi } from '../../../lib/serverApi'
import { proxyErrorResponse } from '../../../lib/proxyError'

export async function GET(_request: Request, { params }: { params: { jobId: string } }) {
  try {
    const response = await serverApi.get(`/api/v1/jobs/${params.jobId}`)
    return NextResponse.json(response.data)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
