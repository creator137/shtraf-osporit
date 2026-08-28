import { Badge } from "@/components/ui/badge"
import type { RecognitionStatus } from "@/lib/api"

const labels: Record<RecognitionStatus, string> = {
  PENDING: "Ожидает OCR",
  PROCESSING: "Распознаётся",
  RECOGNIZED: "Нужна проверка",
  FAILED: "Ошибка OCR",
  VERIFIED: "Проверено",
}

export function RecognitionBadge({
  status,
}: {
  status: RecognitionStatus | null
}) {
  if (!status) return <Badge variant="outline">Не запускалось</Badge>

  return (
    <Badge
      variant={
        status === "VERIFIED"
          ? "default"
          : status === "FAILED"
            ? "destructive"
            : "secondary"
      }
    >
      {labels[status]}
    </Badge>
  )
}
