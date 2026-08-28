import { useMemo, useState } from "react"
import { BriefcaseBusinessIcon, SearchIcon } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"

import { EmptyState, ErrorState, TableLoading } from "@/components/data-feedback"
import { RecognitionBadge } from "@/components/recognition-badge"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useApiResource } from "@/hooks/use-api-resource"
import { getCases } from "@/lib/api"
import { formatDate, formatName } from "@/lib/format"
import { Badge } from "@/components/ui/badge"

export function CasesPage() {
  const navigate = useNavigate()
  const { data: cases, error, loading, retry } = useApiResource(getCases)
  const [query, setQuery] = useState("")
  const [recognitionFilter, setRecognitionFilter] = useState("ALL")
  const filteredCases = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("ru-RU")
    return (cases ?? []).filter((item) => {
      const matchesStatus =
        recognitionFilter === "ALL" ||
        item.recognition_status === recognitionFilter
      const haystack = [
        item.id,
        item.notice_number,
        item.user.telegram_id,
        item.user.username,
        item.user.first_name,
        item.user.last_name,
      ]
        .filter((value) => value !== null)
        .join(" ")
        .toLocaleLowerCase("ru-RU")
      return matchesStatus && (!normalizedQuery || haystack.includes(normalizedQuery))
    })
  }, [cases, query, recognitionFilter])

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold">Дела</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Дела, созданные пользователями Telegram-бота.
        </p>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <>
          {!loading && cases ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardDescription>Всего дел</CardDescription>
                  <CardTitle className="text-2xl">{cases.length}</CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Нужна проверка</CardDescription>
                  <CardTitle className="text-2xl">
                    {
                      cases.filter(
                        (item) => item.recognition_status === "RECOGNIZED"
                      ).length
                    }
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Ошибки OCR</CardDescription>
                  <CardTitle className="text-2xl">
                    {
                      cases.filter((item) => item.recognition_status === "FAILED")
                        .length
                    }
                  </CardTitle>
                </CardHeader>
              </Card>
            </div>
          ) : null}
          <Card>
          <CardHeader>
            <CardTitle>Список дел</CardTitle>
            <CardDescription>Последние 100 дел, новые сверху.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!loading && cases?.length ? (
              <div className="flex flex-col gap-2 sm:flex-row">
                <div className="relative flex-1">
                  <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    className="pl-8"
                    placeholder="ID, постановление или пользователь"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </div>
                <Select
                  value={recognitionFilter}
                  onValueChange={setRecognitionFilter}
                >
                  <SelectTrigger className="w-full sm:w-52">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">Все статусы OCR</SelectItem>
                    <SelectItem value="PENDING">Ожидают OCR</SelectItem>
                    <SelectItem value="PROCESSING">Распознаются</SelectItem>
                    <SelectItem value="RECOGNIZED">Нужна проверка</SelectItem>
                    <SelectItem value="FAILED">Ошибка OCR</SelectItem>
                    <SelectItem value="VERIFIED">Проверено</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            ) : null}
            {!loading && cases?.length === 0 ? (
              <EmptyState
                icon={BriefcaseBusinessIcon}
                title="Дел пока нет"
                description="Созданные через Telegram-бота дела появятся здесь."
              />
            ) : !loading && filteredCases.length === 0 ? (
              <EmptyState
                icon={SearchIcon}
                title="Ничего не найдено"
                description="Измените запрос или статус распознавания."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Постановление</TableHead>
                    <TableHead>Пользователь</TableHead>
                    <TableHead>OCR</TableHead>
                    <TableHead>Поля</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead>Анкета</TableHead>
                    <TableHead>Документы</TableHead>
                    <TableHead>Штраф</TableHead>
                    <TableHead>Создано</TableHead>
                  </TableRow>
                </TableHeader>
                {loading ? (
                  <TableLoading columns={10} />
                ) : (
                  <TableBody>
                    {filteredCases.map((item) => (
                      <TableRow
                        key={item.id}
                        className="cursor-pointer"
                        tabIndex={0}
                        onClick={() => navigate(`/cases/${item.id}`)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault()
                            navigate(`/cases/${item.id}`)
                          }
                        }}
                      >
                        <TableCell>
                          <Button variant="link" size="sm" asChild>
                            <Link
                              to={`/cases/${item.id}`}
                              onClick={(event) => event.stopPropagation()}
                            >
                              #{item.id}
                            </Link>
                          </Button>
                        </TableCell>
                        <TableCell className="font-medium">
                          {item.notice_number ?? "Не определено"}
                        </TableCell>
                        <TableCell>{formatName(item.user)}</TableCell>
                        <TableCell>
                          <RecognitionBadge status={item.recognition_status} />
                        </TableCell>
                        <TableCell>{item.recognized_fields_count} / 9</TableCell>
                        <TableCell>
                          <StatusBadge status={item.status} />
                        </TableCell>
                        <TableCell>
                          {item.legal_assessment_status === "COMPLETED" ? (
                            <Badge>Завершена</Badge>
                          ) : item.legal_assessment_status === "IN_PROGRESS" ? (
                            <Badge variant="secondary">В процессе</Badge>
                          ) : (
                            <span className="text-sm text-muted-foreground">Не начата</span>
                          )}
                        </TableCell>
                        <TableCell>{item.documents_count}</TableCell>
                        <TableCell>
                          {item.fine_amount === null
                            ? "Не определён"
                            : `${item.fine_amount.toLocaleString("ru-RU")} ₽`}
                        </TableCell>
                        <TableCell>{formatDate(item.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                )}
              </Table>
            )}
          </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
