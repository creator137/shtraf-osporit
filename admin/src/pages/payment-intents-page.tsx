import { useCallback } from "react"
import { HandCoinsIcon } from "lucide-react"
import { Link } from "react-router-dom"

import { EmptyState, ErrorState, TableLoading } from "@/components/data-feedback"
import { Badge } from "@/components/ui/badge"
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
import {
  getPaymentIntents,
  getPaymentIntentStats,
  type PaymentIntentItem,
  type PaymentIntentStats,
} from "@/lib/api"
import { formatDate, formatName, formatUsername } from "@/lib/format"

interface PaymentInterestData {
  stats: PaymentIntentStats
  intents: PaymentIntentItem[]
}

export function PaymentIntentsPage() {
  const loadData = useCallback(async (): Promise<PaymentInterestData> => {
    const [stats, intents] = await Promise.all([
      getPaymentIntentStats(),
      getPaymentIntents(),
    ])
    return { stats, intents }
  }, [])
  const { data, error, loading, retry } = useApiResource(loadData)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold">Интерес к оплате</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Переходы пользователей к оплате тестовых предложений. Деньги не принимаются.
        </p>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            {loading || !data ? (
              Array.from({ length: 3 }, (_, index) => (
                <Card key={index}>
                  <CardHeader>
                    <Skeleton className="h-4 w-36" />
                    <Skeleton className="h-8 w-20" />
                  </CardHeader>
                </Card>
              ))
            ) : (
              <>
                <MetricCard label="Переходов к оплате" value={data.stats.total_clicks} />
                <MetricCard
                  label="Уникальных пользователей"
                  value={data.stats.unique_users}
                />
                <MetricCard label="Уникальных дел" value={data.stats.unique_cases} />
              </>
            )}
          </div>

          {!loading && data ? (
            <div className="grid gap-3 md:grid-cols-3">
              {data.stats.offers.map((offer) => (
                <Card key={offer.offer_code}>
                  <CardHeader>
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle>{offer.title}</CardTitle>
                      <Badge variant="outline">{offer.price}</Badge>
                    </div>
                    <CardDescription>{offer.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground">Переходов</div>
                      <div className="mt-1 text-lg font-semibold">{offer.clicks}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Пользователей</div>
                      <div className="mt-1 text-lg font-semibold">
                        {offer.unique_users}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Последние переходы</CardTitle>
              <CardDescription>Последние 100 нажатий, новые сверху.</CardDescription>
            </CardHeader>
            <CardContent>
              {!loading && data?.intents.length === 0 ? (
                <EmptyState
                  icon={HandCoinsIcon}
                  title="Переходов пока нет"
                  description="События появятся после нажатия кнопки оплаты в Telegram."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Дата</TableHead>
                      <TableHead>Пользователь</TableHead>
                      <TableHead>Дело</TableHead>
                      <TableHead>Предложение</TableHead>
                      <TableHead>Цена</TableHead>
                    </TableRow>
                  </TableHeader>
                  {loading || !data ? (
                    <TableLoading columns={5} />
                  ) : (
                    <TableBody>
                      {data.intents.map((intent) => (
                        <TableRow key={intent.id}>
                          <TableCell>{formatDate(intent.created_at)}</TableCell>
                          <TableCell>
                            <div className="font-medium">{formatName(intent.user)}</div>
                            <div className="text-sm text-muted-foreground">
                              {formatUsername(intent.user.username)}
                            </div>
                          </TableCell>
                          <TableCell>
                            {intent.case_id ? (
                              <Link
                                className="font-medium hover:underline"
                                to={`/cases/${intent.case_id}`}
                              >
                                Дело №{intent.case_id}
                              </Link>
                            ) : (
                              "Без дела"
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{intent.offer_title}</Badge>
                          </TableCell>
                          <TableCell>{intent.price}</TableCell>
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

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  )
}
