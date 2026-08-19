import { NextResponse } from 'next/server'
import { AxiosError } from 'axios'

// Traduit une erreur axios (appel vers l'API distante) en réponse JSON pour
// les routes proxy sous web/app/api/**.
export function proxyErrorResponse(error: unknown): NextResponse {
  const axiosError = error as AxiosError<{ detail?: string }>
  const statusCode = axiosError.response?.status || 500
  const detail = axiosError.response?.data?.detail || 'Erreur serveur'
  return NextResponse.json({ error: detail }, { status: statusCode })
}
