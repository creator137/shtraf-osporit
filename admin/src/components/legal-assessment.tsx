import { ClipboardListIcon, ScaleIcon } from "lucide-react"

import { EmptyState } from "@/components/data-feedback"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type {
  EvidenceStatus,
  LegalAssessmentItem,
} from "@/lib/api"
import { formatDate } from "@/lib/format"

const evidenceLabels: Record<EvidenceStatus, string> = {
  AVAILABLE: "Материалы указаны",
  NEEDED: "Нужны доказательства",
  VERIFY: "Требуется проверка",
}

export function LegalAssessmentView({
  assessment,
}: {
  assessment: LegalAssessmentItem | null
}) {
  if (!assessment) {
    return (
      <EmptyState
        icon={ClipboardListIcon}
        title="Анкета ещё не пройдена"
        description="Ответы пользователя и направления проверки появятся после прохождения анкеты в Telegram."
      />
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={assessment.status === "COMPLETED" ? "default" : "secondary"}>
          {assessment.status === "COMPLETED" ? "Завершена" : "В процессе"}
        </Badge>
        <span className="text-sm text-muted-foreground">
          Версия правил: {assessment.rules_version}
        </span>
        <span className="text-sm text-muted-foreground">
          Обновлено: {formatDate(assessment.updated_at)}
        </span>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Ответы пользователя</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Вопрос</TableHead>
              <TableHead>Ответ</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assessment.answers.map((item) => (
              <TableRow key={item.question_id}>
                <TableCell className="max-w-2xl whitespace-normal">
                  {item.question}
                </TableCell>
                <TableCell className="font-medium">{item.answer}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Направления проверки</h3>
        {assessment.status !== "COMPLETED" ? (
          <p className="text-sm text-muted-foreground">
            Результат появится после завершения анкеты.
          </p>
        ) : assessment.results.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            По ответам явные направления проверки не определены.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {assessment.results.map((result) => (
              <div key={result.code} className="rounded-md border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <ScaleIcon className="size-4 text-muted-foreground" />
                  <Badge variant="outline">{result.code}</Badge>
                  <h4 className="text-sm font-semibold">{result.title}</h4>
                  <Badge variant="secondary">
                    {evidenceLabels[result.evidence_status]}
                  </Badge>
                </div>
                <p className="mt-2 text-sm">{result.direction}</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {result.legal_basis}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Необходимо: {result.required_evidence.join(", ")}.
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
