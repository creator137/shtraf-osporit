export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export type CaseStatus = "DOCUMENT_UPLOADED" | "IN_PROGRESS" | "READY"
export type RecognitionStatus =
  | "PENDING"
  | "PROCESSING"
  | "RECOGNIZED"
  | "FAILED"
  | "VERIFIED"

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
  consent_version: string | null
  consent_accepted_at: string | null
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

export interface RecognitionItem {
  id: number
  document_id: number
  status: RecognitionStatus
  raw_text: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface FineNoticeItem {
  notice_number: string | null
  notice_date: string | null
  uin: string | null
  fine_amount: number | null
  article: string | null
  vehicle_plate: string | null
  violation_datetime: string | null
  violation_place: string | null
  issuing_authority: string | null
}

export interface CaseDetail {
  id: number
  status: CaseStatus
  created_at: string
  updated_at: string
  user: UserSummary
  documents: DocumentItem[]
  recognition: RecognitionItem | null
  fine_notice: FineNoticeItem | null
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, options)
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

  if (response.status === 204) {
    return undefined as T
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

export function updateCaseStatus(
  caseId: number,
  status: CaseStatus
): Promise<CaseDetail> {
  return request(`/admin/cases/${caseId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  })
}

export function updateFineNotice(
  caseId: number,
  payload: Partial<FineNoticeItem>
): Promise<CaseDetail> {
  return request(`/admin/cases/${caseId}/fine-notice`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export function recognizeCaseDocument(caseId: number): Promise<CaseDetail> {
  return request(`/admin/cases/${caseId}/recognize`, { method: "POST" })
}

export function deleteCase(caseId: number): Promise<void> {
  return request(`/admin/cases/${caseId}`, { method: "DELETE" })
}

export function getDocumentFileUrl(documentId: number): string {
  return `${API_URL}/admin/documents/${documentId}/file`
}
