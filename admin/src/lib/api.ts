export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export type CaseStatus = "DOCUMENT_UPLOADED" | "IN_PROGRESS" | "READY"
export type RecognitionStatus =
  | "PENDING"
  | "PROCESSING"
  | "RECOGNIZED"
  | "FAILED"
  | "VERIFIED"
export type LegalAssessmentStatus = "IN_PROGRESS" | "COMPLETED"
export type EvidenceStatus = "AVAILABLE" | "NEEDED" | "VERIFY"

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
  recognition_status: RecognitionStatus | null
  notice_number: string | null
  fine_amount: number | null
  recognized_fields_count: number
  legal_assessment_status: LegalAssessmentStatus | null
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

export interface LegalAnswerItem {
  question_id: string
  question: string
  value: string
  answer: string
}

export interface LegalRuleItem {
  code: string
  title: string
  direction: string
  legal_basis: string
  required_evidence: string[]
  source_ids: string[]
}

export interface LegalEvidenceItem {
  name: string
  status: EvidenceStatus
}

export interface LegalRuleResult extends LegalRuleItem {
  evidence_status: EvidenceStatus
  evidence_items: LegalEvidenceItem[]
  reasons: string[]
}

export interface LegalVersionItem {
  version: string
  effective_from: string
  title: string
}

export interface LegalAssessmentItem {
  status: LegalAssessmentStatus
  rules_version: string
  answers: LegalAnswerItem[]
  results: LegalRuleResult[]
  completed_at: string | null
  updated_at: string
}

export interface LegalAnalysisItem {
  status: string
  provider: string
  model: string
  summary: string | null
  overall_assessment: string | null
  grounds: Array<Record<string, unknown>>
  missing_evidence: string[]
  document_evidence_review: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface GeneratedDocumentItem {
  id: number
  document_type: string
  file_format: string
  original_filename: string
  created_at: string
}

export interface PaymentOfferStats {
  offer_code: string
  title: string
  description: string
  price: string
  clicks: number
  unique_users: number
}

export interface PaymentIntentStats {
  total_clicks: number
  unique_users: number
  unique_cases: number
  offers: PaymentOfferStats[]
}

export interface PaymentIntentItem {
  id: number
  created_at: string
  user_id: number
  user: UserSummary
  case_id: number | null
  offer_code: string
  offer_title: string
  price: string
}

export interface LegalSourceItem {
  id: string
  title: string
  reference: string
  effective_note: string
  document_available: boolean
}

export interface LegalKnowledgeBase {
  rules: LegalRuleItem[]
  versions: LegalVersionItem[]
  sources: LegalSourceItem[]
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
  recognized_fields_count: number
  legal_assessment: LegalAssessmentItem | null
  legal_analysis: LegalAnalysisItem | null
  generated_documents: GeneratedDocumentItem[]
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, options)
  } catch {
    throw new Error("API недоступен. Проверьте, что backend запущен.")
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg?: string }>
    } | null
    const detail = Array.isArray(payload?.detail)
      ? payload.detail.map((item) => item.msg).filter(Boolean).join(". ")
      : payload?.detail
    throw new Error(
      detail ||
        (response.status === 404
          ? "Запрошенная запись не найдена."
          : "Backend вернул ошибку. Попробуйте еще раз.")
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

export function getLegalRules(): Promise<LegalKnowledgeBase> {
  return request("/admin/legal-rules")
}

export function getPaymentIntentStats(): Promise<PaymentIntentStats> {
  return request("/admin/payment-intents/stats")
}

export function getPaymentIntents(): Promise<PaymentIntentItem[]> {
  return request("/admin/payment-intents")
}

export function getLegalSourceFileUrl(sourceId: string): string {
  return `${API_URL}/admin/legal-sources/${sourceId}/file`
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

export function sendQuestionnaire(caseId: number): Promise<void> {
  return request(`/admin/cases/${caseId}/send-questionnaire`, { method: "POST" })
}

export function getDocumentFileUrl(documentId: number): string {
  return `${API_URL}/admin/documents/${documentId}/file`
}

export function getGeneratedDocumentFileUrl(documentId: number): string {
  return `${API_URL}/admin/generated-documents/${documentId}/file`
}
