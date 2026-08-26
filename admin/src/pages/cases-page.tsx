import { BriefcaseBusinessIcon } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"

import { EmptyState, ErrorState, TableLoading } from "@/components/data-feedback"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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

export function CasesPage() {
  const navigate = useNavigate()
  const { data: cases, error, loading, retry } = useApiResource(getCases)

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
        <Card>
          <CardHeader>
            <CardTitle>Список дел</CardTitle>
            <CardDescription>Последние 100 дел, новые сверху.</CardDescription>
          </CardHeader>
          <CardContent>
            {!loading && cases?.length === 0 ? (
              <EmptyState
                icon={BriefcaseBusinessIcon}
                title="Дел пока нет"
                description="Созданные через Telegram-бота дела появятся здесь."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Пользователь</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead>Документы</TableHead>
                    <TableHead>Создано</TableHead>
                  </TableRow>
                </TableHeader>
                {loading ? (
                  <TableLoading columns={5} />
                ) : (
                  <TableBody>
                    {cases?.map((item) => (
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
                        <TableCell>{formatName(item.user)}</TableCell>
                        <TableCell>
                          <StatusBadge status={item.status} />
                        </TableCell>
                        <TableCell>{item.documents_count}</TableCell>
                        <TableCell>{formatDate(item.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                )}
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
