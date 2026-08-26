import { Badge } from "@/components/ui/badge"
import type { CaseStatus } from "@/lib/api"

const labels: Record<CaseStatus, string> = {
  DOCUMENT_UPLOADED: "Документ загружен",
  IN_PROGRESS: "Документ в работе",
  READY: "Готов",
}

export function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <Badge variant={status === "READY" ? "default" : "secondary"}>
      {labels[status]}
    </Badge>
  )
}
