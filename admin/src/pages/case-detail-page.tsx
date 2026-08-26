import { useCallback } from "react"
import { ArrowLeftIcon, FileTextIcon } from "lucide-react"
import { Link, useParams } from "react-router-dom"

import { EmptyState, ErrorState } from "@/components/data-feedback"
import { StatusBadge } from "@/components/status-badge"
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
import { getCase } from "@/lib/api"
import { formatDate, formatName, formatUsername } from "@/lib/format"

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

export function CaseDetailPage() {
  const { caseId = "" } = useParams()
  const numericCaseId = Number(caseId)
  const loadCase = useCallback(() => getCase(numericCaseId), [numericCaseId])
  const { data: item, error, loading, retry } = useApiResource(loadCase)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Дело №{caseId}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Основная информация и загруженные документы.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/cases">
            <ArrowLeftIcon data-icon="inline-start" />
            К списку дел
          </Link>
        </Button>
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
                <DetailRow label="Статус" value={<StatusBadge status={item.status} />} />
                <DetailRow label="Создано" value={formatDate(item.created_at)} />
                <DetailRow label="Обновлено" value={formatDate(item.updated_at)} />
              </dl>
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
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
