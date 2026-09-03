import { useCallback, useEffect, useState } from "react"
import {
  ArrowLeftIcon,
  ExternalLinkIcon,
  FileSearchIcon,
  FileTextIcon,
  Trash2Icon,
} from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { EmptyState, ErrorState } from "@/components/data-feedback"
import { FineNoticeForm } from "@/components/fine-notice-form"
import { LegalAssessmentView } from "@/components/legal-assessment"
import { RecognitionBadge } from "@/components/recognition-badge"
import { StatusBadge } from "@/components/status-badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useApiResource } from "@/hooks/use-api-resource"
import { emptyFineNotice } from "@/lib/fine-notice"
import {
  deleteCase,
  getCase,
  getDocumentFileUrl,
  getGeneratedDocumentFileUrl,
  recognizeCaseDocument,
  sendQuestionnaire,
  updateCaseStatus,
  updateFineNotice,
  type CaseStatus,
  type FineNoticeItem,
} from "@/lib/api"
import { formatDate, formatName, formatUsername } from "@/lib/format"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

function DetailLoading() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {Array.from({ length: 3 }, (_, index) => (
        <Card key={index} className={index === 2 ? "lg:col-span-2" : undefined}>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Skeleton className="h-4 w-full max-w-72" />
            <Skeleton className="h-4 w-full max-w-56" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[9rem_1fr] sm:gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words font-medium">{value}</dd>
    </div>
  )
}

function textValue(value: unknown): string {
  return typeof value === "string" ? value : ""
}

function listValue(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : []
}

const analysisStatusLabels: Record<string, string> = {
  PENDING_CONFIRMATION: "Ожидает подтверждения",
  CONFIRMED: "Основания подтверждены",
  DOCUMENTS_GENERATED: "Документы сформированы",
  FAILED: "Ошибка анализа",
}

const groundStatusLabels: Record<string, string> = {
  PROPOSED: "Предложено системой",
  CONFIRMED: "Подтверждено пользователем",
  REJECTED: "Отклонено пользователем",
}

const sourceLabels: Record<string, string> = {
  "koap-rf": "КоАП РФ",
  "plenum-vs-20": "Постановление Пленума Верховного Суда РФ № 20",
}

const documentTypeLabels: Record<string, string> = {
  COMPLAINT: "Жалоба на постановление",
  EVIDENCE_PETITION: "Ходатайство об истребовании доказательств",
}

export function CaseDetailPage() {
  const { caseId = "" } = useParams()
  const navigate = useNavigate()
  const numericCaseId = Number(caseId)
  const loadCase = useCallback(() => getCase(numericCaseId), [numericCaseId])
  const { data: item, error, loading, retry } = useApiResource(loadCase)
  const [status, setStatus] = useState<CaseStatus | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [statusSaving, setStatusSaving] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [notice, setNotice] = useState<FineNoticeItem>(emptyFineNotice)
  const [noticeSaving, setNoticeSaving] = useState(false)
  const [noticeError, setNoticeError] = useState<string | null>(null)
  const [recognizing, setRecognizing] = useState(false)
  const [recognitionError, setRecognitionError] = useState<string | null>(null)
  const [questionnaireSending, setQuestionnaireSending] = useState(false)
  const [questionnaireError, setQuestionnaireError] = useState<string | null>(null)
  const [questionnaireSent, setQuestionnaireSent] = useState(false)

  useEffect(() => {
    if (item) setStatus(item.status)
  }, [item])

  useEffect(() => {
    if (item) setNotice(item.fine_notice ?? emptyFineNotice)
  }, [item])

  async function handleStatusChange(nextStatus: string) {
    const next = nextStatus as CaseStatus
    setStatus(next)
    setStatusError(null)
    setStatusSaving(true)
    try {
      const updated = await updateCaseStatus(numericCaseId, next)
      setStatus(updated.status)
      retry()
    } catch (caught) {
      setStatus(item?.status ?? null)
      setStatusError(
        caught instanceof Error ? caught.message : "Не удалось изменить статус."
      )
    } finally {
      setStatusSaving(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Удалить дело №${caseId} и все его документы?`)) return

    setDeleteError(null)
    setDeleting(true)
    try {
      await deleteCase(numericCaseId)
      navigate("/cases")
    } catch (caught) {
      setDeleteError(
        caught instanceof Error ? caught.message : "Не удалось удалить дело."
      )
    } finally {
      setDeleting(false)
    }
  }

  async function handleNoticeSave() {
    setNoticeError(null)
    setNoticeSaving(true)
    try {
      const updated = await updateFineNotice(numericCaseId, notice)
      setNotice(updated.fine_notice ?? emptyFineNotice)
      retry()
    } catch (caught) {
      setNoticeError(
        caught instanceof Error ? caught.message : "Не удалось сохранить данные."
      )
    } finally {
      setNoticeSaving(false)
    }
  }

  async function handleRecognize() {
    setRecognitionError(null)
    setRecognizing(true)
    try {
      await recognizeCaseDocument(numericCaseId)
      retry()
    } catch (caught) {
      setRecognitionError(
        caught instanceof Error
          ? caught.message
          : "Не удалось запустить распознавание."
      )
    } finally {
      setRecognizing(false)
    }
  }

  async function handleSendQuestionnaire() {
    setQuestionnaireError(null)
    setQuestionnaireSent(false)
    setQuestionnaireSending(true)
    try {
      await sendQuestionnaire(numericCaseId)
      setQuestionnaireSent(true)
    } catch (caught) {
      setQuestionnaireError(
        caught instanceof Error
          ? caught.message
          : "Не удалось отправить анкету клиенту."
      )
    } finally {
      setQuestionnaireSending(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Дело №{caseId}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Основная информация и загруженные документы.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={handleSendQuestionnaire}
            disabled={questionnaireSending}
          >
            <FileSearchIcon data-icon="inline-start" />
            {questionnaireSending
              ? "Отправка анкеты..."
              : "Отправить анкету клиенту"}
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleting}
          >
            <Trash2Icon data-icon="inline-start" />
            {deleting ? "Удаление..." : "Удалить дело"}
          </Button>
          <Button variant="outline" asChild>
            <Link to="/cases">
              <ArrowLeftIcon data-icon="inline-start" />
              К списку дел
            </Link>
          </Button>
        </div>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : loading || !item ? (
        <DetailLoading />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Основное</CardTitle>
              <CardDescription>Текущее состояние дела.</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-3">
                <DetailRow label="Номер дела" value={`№${item.id}`} />
                <DetailRow
                  label="Статус"
                  value={
                    <div className="flex flex-wrap items-center gap-2">
                      <Select
                        value={status ?? item.status}
                        onValueChange={handleStatusChange}
                        disabled={statusSaving}
                      >
                        <SelectTrigger className="w-52">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="DOCUMENT_UPLOADED">
                            Документ загружен
                          </SelectItem>
                          <SelectItem value="IN_PROGRESS">
                            Документ в работе
                          </SelectItem>
                          <SelectItem value="READY">Готов</SelectItem>
                        </SelectContent>
                      </Select>
                      {statusSaving ? (
                        <span className="text-sm text-muted-foreground">Сохранение...</span>
                      ) : null}
                    </div>
                  }
                />
                <DetailRow
                  label="Текущий статус"
                  value={<StatusBadge status={status ?? item.status} />}
                />
                <DetailRow label="Создано" value={formatDate(item.created_at)} />
                <DetailRow label="Обновлено" value={formatDate(item.updated_at)} />
              </dl>
              {statusError ? (
                <Alert variant="destructive" className="mt-4">
                  <AlertTitle>Статус не изменён</AlertTitle>
                  <AlertDescription>{statusError}</AlertDescription>
                </Alert>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Пользователь</CardTitle>
              <CardDescription>Данные из Telegram-профиля.</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-3">
                <DetailRow label="Имя" value={formatName(item.user)} />
                <DetailRow label="Username" value={formatUsername(item.user.username)} />
                <DetailRow label="Telegram ID" value={item.user.telegram_id} />
              </dl>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Документы</CardTitle>
              <CardDescription>Файлы, загруженные для этого дела.</CardDescription>
            </CardHeader>
            <CardContent>
              {item.documents.length === 0 ? (
                <EmptyState
                  icon={FileTextIcon}
                  title="Документов пока нет"
                  description="Пользователь еще не загрузил постановление."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Название</TableHead>
                      <TableHead>MIME type</TableHead>
                      <TableHead>Загружен</TableHead>
                      <TableHead className="text-right">Действия</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {item.documents.map((document) => (
                      <TableRow key={document.id}>
                        <TableCell className="font-medium">
                          {document.original_filename ?? "Без названия"}
                        </TableCell>
                        <TableCell>{document.mime_type ?? "Не указан"}</TableCell>
                        <TableCell>{formatDate(document.created_at)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="outline" size="sm" asChild>
                            <a
                              href={getDocumentFileUrl(document.id)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              <ExternalLinkIcon data-icon="inline-start" />
                              Открыть
                            </a>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Распознавание</CardTitle>
                  <CardDescription>
                    Текст постановления и статус обработки документа.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  onClick={handleRecognize}
                  disabled={
                    recognizing ||
                    item.documents.length === 0 ||
                    item.recognition?.status === "VERIFIED"
                  }
                >
                  <FileSearchIcon data-icon="inline-start" />
                  {recognizing ? "Распознавание..." : "Распознать"}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <dl className="flex flex-col gap-3">
                <DetailRow
                  label="Статус"
                  value={<RecognitionBadge status={item.recognition?.status ?? null} />}
                />
                {item.recognition?.error_message ? (
                  <DetailRow label="Ошибка" value={item.recognition.error_message} />
                ) : null}
              </dl>
              <div className="rounded-md border bg-muted/30 p-3">
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-sm">
                  {item.recognition?.raw_text ||
                    "Текст распознавания пока не сохранён."}
                </pre>
              </div>
              {recognitionError ? (
                <Alert variant="destructive">
                  <AlertTitle>Распознавание не выполнено</AlertTitle>
                  <AlertDescription>{recognitionError}</AlertDescription>
                </Alert>
              ) : null}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Данные постановления</CardTitle>
                  <CardDescription>
                    Проверьте результат OCR и подтвердите карточку дела.
                  </CardDescription>
                </div>
                <Badge variant="outline">
                  Заполнено {item.recognized_fields_count} из 9
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <FineNoticeForm
                notice={notice}
                original={item.fine_notice ?? emptyFineNotice}
                saving={noticeSaving}
                error={noticeError}
                onChange={setNotice}
                onSave={handleNoticeSave}
              />
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Юридическая анкета</CardTitle>
              <CardDescription>
                Ответы пользователя и определённые системой направления проверки.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LegalAssessmentView
                assessment={item.legal_assessment}
                onSendToClient={handleSendQuestionnaire}
                sending={questionnaireSending}
              />
              {questionnaireSent ? (
                <p className="mt-3 text-sm text-emerald-600">
                  Анкета отправлена клиенту в Telegram.
                </p>
              ) : null}
              {questionnaireError ? (
                <p className="mt-3 text-sm text-destructive">
                  {questionnaireError}
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Юридический анализ</CardTitle>
              <CardDescription>
                Предложенные основания, статусы подтверждения и недостающие доказательства.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!item.legal_analysis ? (
                <EmptyState
                  icon={FileSearchIcon}
                  title="Анализ ещё не выполнен"
                  description="После анализа здесь появятся предложенные основания и сведения для проверки."
                />
              ) : (
                <div className="flex flex-col gap-4">
                  <dl className="flex flex-col gap-3">
                    <DetailRow
                      label="Статус"
                      value={
                        analysisStatusLabels[item.legal_analysis.status] ??
                        "Статус не определён"
                      }
                    />
                    <DetailRow label="Модель" value={item.legal_analysis.model} />
                    <DetailRow
                      label="Итог"
                      value={item.legal_analysis.overall_assessment ?? "Не указан"}
                    />
                    <DetailRow
                      label="Кратко"
                      value={item.legal_analysis.summary ?? "Не указано"}
                    />
                  </dl>
                  <div>
                    <h3 className="mb-2 text-sm font-semibold">Основания</h3>
                    {item.legal_analysis.grounds.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        Валидные основания не сохранены.
                      </p>
                    ) : (
                      <div className="flex flex-col gap-3">
                        {item.legal_analysis.grounds.map((ground) => (
                          <div
                            key={textValue(ground.id)}
                            className="rounded-md border p-4 text-sm"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold">
                                {textValue(ground.title)}
                              </span>
                              <Badge variant="secondary">
                                {groundStatusLabels[textValue(ground.status)] ??
                                  "Ожидает решения"}
                              </Badge>
                            </div>
                            <p className="mt-2 text-muted-foreground">
                              {textValue(ground.description)}
                            </p>
                            <p className="mt-2">
                              Юридические правила:{" "}
                              {listValue(ground.legal_rule_ids).join(", ") ||
                                "не указаны"}
                            </p>
                            <p>
                              Источники: {listValue(ground.source_ids)
                                .map((source) => sourceLabels[source] ?? source)
                                .join(", ") || "не указаны"}
                            </p>
                            <p>
                              Что нужно дополнительно:{" "}
                              {listValue(ground.missing_evidence).join(", ") ||
                                "ничего"}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div>
                    <h3 className="mb-2 text-sm font-semibold">
                      Недостающие доказательства
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {item.legal_analysis.missing_evidence.join(", ") || "Нет"}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Сформированные документы</CardTitle>
              <CardDescription>
                Документы, сформированные по подтверждённым основаниям.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {item.generated_documents.length === 0 ? (
                <EmptyState
                  icon={FileTextIcon}
                  title="Документы ещё не сформированы"
                  description="После генерации здесь появятся DOCX и PDF."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Тип</TableHead>
                      <TableHead>Формат</TableHead>
                      <TableHead>Создан</TableHead>
                      <TableHead className="text-right">Действия</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {item.generated_documents.map((document) => (
                      <TableRow key={document.id}>
                        <TableCell>
                          {documentTypeLabels[document.document_type] ?? "Документ"}
                        </TableCell>
                        <TableCell>{document.file_format}</TableCell>
                        <TableCell>{formatDate(document.created_at)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="outline" size="sm" asChild>
                            <a
                              href={getGeneratedDocumentFileUrl(document.id)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              <ExternalLinkIcon data-icon="inline-start" />
                              Открыть
                            </a>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
      {deleteError ? (
        <Alert variant="destructive">
          <AlertTitle>Дело не удалено</AlertTitle>
          <AlertDescription>{deleteError}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  )
}
