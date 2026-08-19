import { NextResponse } from 'next/server'
import { serverApi } from '../../../../lib/serverApi'
import { proxyErrorResponse } from '../../../../lib/proxyError'

export async function GET(_request: Request, { params }: { params: { jobId: string } }) {
  try {
    const response = await serverApi.get(`/api/v1/restore/${params.jobId}/download`, {
      responseType: 'arraybuffer',
    })
    return new NextResponse(response.data, {
      status: 200,
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="restore_${params.jobId}.zip"`,
      },
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
