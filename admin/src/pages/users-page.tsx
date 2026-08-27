import { UsersIcon } from "lucide-react"

import { EmptyState, ErrorState, TableLoading } from "@/components/data-feedback"
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
import { getUsers } from "@/lib/api"
import { formatDate, formatName, formatUsername } from "@/lib/format"

export function UsersPage() {
  const { data: users, error, loading, retry } = useApiResource(getUsers)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold">Пользователи</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Пользователи, зарегистрированные через Telegram-бота.
        </p>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Список пользователей</CardTitle>
            <CardDescription>Последние 100 регистраций.</CardDescription>
          </CardHeader>
          <CardContent>
            {!loading && users?.length === 0 ? (
              <EmptyState
                icon={UsersIcon}
                title="Пользователей пока нет"
                description="Новые пользователи появятся после запуска Telegram-бота."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Telegram ID</TableHead>
                    <TableHead>Пользователь</TableHead>
                    <TableHead>Username</TableHead>
                    <TableHead>Количество дел</TableHead>
                    <TableHead>Согласие</TableHead>
                    <TableHead>Дата регистрации</TableHead>
                  </TableRow>
                </TableHeader>
                {loading ? (
                  <TableLoading columns={7} />
                ) : (
                  <TableBody>
                    {users?.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.id}</TableCell>
                        <TableCell>{user.telegram_id}</TableCell>
                        <TableCell>{formatName(user)}</TableCell>
                        <TableCell>{formatUsername(user.username)}</TableCell>
                        <TableCell>{user.cases_count}</TableCell>
                        <TableCell>
                          {user.consent_accepted_at
                            ? `${formatDate(user.consent_accepted_at)} (${user.consent_version})`
                            : "Нет"}
                        </TableCell>
                        <TableCell>{formatDate(user.created_at)}</TableCell>
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
