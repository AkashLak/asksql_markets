import type { AskResponse } from './types'

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? res.statusText)
  }
  return res.json()
}
