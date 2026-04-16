export interface AskResponse {
  sql: string | null
  columns: string[]
  results: (string | number | null)[][]
  explanation: string
  success: boolean
  error: string | null
}
