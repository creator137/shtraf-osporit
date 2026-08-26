const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export type CaseStatus = "NEW" | "DOCUMENT_UPLOADED"

export interface UserSummary {
  telegram_id: number
  username: string | null
  first_name: string | null
  last_name: string | null
}

export interface UserListItem extends UserSummary {
  id: number
  created_at: string
  cases_count: number
}

export interface CaseListItem {
  id: number
  status: CaseStatus
  created_at: string
  user: UserSummary
  documents_count: number
}

export interface DocumentItem {
  id: number
  original_filename: string | null
  mime_type: string | null
  created_at: string
}

export interface CaseDetail {
  id: number
  status: CaseStatus
  created_at: string
  updated_at: string
  user: UserSummary
  documents: DocumentItem[]
}

async function request<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`)
  } catch {
    throw new Error("API недоступен. Проверьте, что backend запущен.")
  }

  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? "Запрошенная запись не найдена."
        : "Backend вернул ошибку. Попробуйте еще раз."
    )
  }

  return response.json() as Promise<T>
}

export function getUsers(): Promise<UserListItem[]> {
  return request("/admin/users")
}

export function getCases(): Promise<CaseListItem[]> {
  return request("/admin/cases")
}

export function getCase(caseId: number): Promise<CaseDetail> {
  return request(`/admin/cases/${caseId}`)
}
