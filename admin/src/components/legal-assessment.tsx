import { ClipboardListIcon, ScaleIcon, SendIcon } from "lucide-react"

import { EmptyState } from "@/components/data-feedback"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
  AVAILABLE: "Подтверждение есть",
  NEEDED: "Нужны материалы",
  VERIFY: "Нужно проверить",
}

export function LegalAssessmentView({
  assessment,
  onSendToClient,
  sending,
}: {
  assessment: LegalAssessmentItem | null
  onSendToClient: () => void
  sending: boolean
}) {
  if (!assessment) {
    return (
      <div className="flex flex-col gap-4">
        <EmptyState
          icon={ClipboardListIcon}
          title="Анкета ещё не пройдена"
          description="Ответы пользователя и направления проверки появятся после прохождения анкеты в Telegram."
        />
        <Button
          className="self-start"
          variant="outline"
          onClick={onSendToClient}
          disabled={sending}
        >
          <SendIcon data-icon="inline-start" />
          {sending ? "Отправка..." : "Отправить анкету клиенту"}
        </Button>
      </div>
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
        {assessment.completed_at ? (
          <span className="text-sm text-muted-foreground">
            Завершено: {formatDate(assessment.completed_at)}
          </span>
        ) : null}
        <span className="text-sm text-muted-foreground">
          Обновлено: {formatDate(assessment.updated_at)}
        </span>
        <Button
          className="ml-auto"
          variant="outline"
          size="sm"
          onClick={onSendToClient}
          disabled={sending}
        >
          <SendIcon data-icon="inline-start" />
          {sending ? "Отправка..." : "Отправить анкету клиенту"}
        </Button>
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
        <h3 className="mb-2 text-sm font-semibold">
          Результат предварительной проверки оснований для обжалования
        </h3>
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
                  Почему выбрано это направление: {(result.reasons ?? []).join(" ")}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {result.legal_basis}
                </p>
                <div className="mt-3 flex flex-col gap-2 text-sm">
                  {(result.evidence_items ?? []).map((item) => (
                    <div key={`${result.code}-${item.name}`} className="flex flex-wrap gap-2">
                      <Badge variant="outline">{evidenceLabels[item.status]}</Badge>
                      <span>{item.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
