import { Badge } from "@/components/ui/badge"
import type { CaseStatus } from "@/lib/api"

const labels: Record<CaseStatus, string> = {
  NEW: "Новое",
  DOCUMENT_UPLOADED: "Документ загружен",
}

export function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <Badge variant={status === "DOCUMENT_UPLOADED" ? "default" : "secondary"}>
      {labels[status]}
    </Badge>
  )
}
