import { ExternalLinkIcon, ScaleIcon } from "lucide-react"

import { ErrorState, TableLoading } from "@/components/data-feedback"
import { Badge } from "@/components/ui/badge"
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
import { getLegalRules, getLegalSourceFileUrl } from "@/lib/api"

export function LegalRulesPage() {
  const { data, error, loading, retry } = useApiResource(getLegalRules)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold">Юридические правила</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Версионированные направления проверки, используемые анкетой Stage 3.
        </p>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <>
          <div className="grid gap-3 lg:grid-cols-2">
            {(data?.sources ?? []).map((source) => (
              <Card key={source.id}>
                <CardHeader>
                  <CardTitle className="text-base">{source.title}</CardTitle>
                  <CardDescription>{source.reference}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col items-start gap-3">
                  <p className="text-sm text-muted-foreground">
                    {source.effective_note}
                  </p>
                  {source.document_available ? (
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={getLegalSourceFileUrl(source.id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <ExternalLinkIcon data-icon="inline-start" />
                        Открыть источник
                      </a>
                    </Button>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ScaleIcon className="size-5 text-muted-foreground" />
                <CardTitle>Сценарии MVP</CardTitle>
              </div>
              <CardDescription>
                Система выводит эти направления из фактических ответов пользователя.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-3 md:hidden">
                {loading
                  ? Array.from({ length: 3 }, (_, index) => (
                      <div key={index} className="h-36 animate-pulse rounded-md bg-muted" />
                    ))
                  : (data?.rules ?? []).map((rule) => (
                      <div key={rule.code} className="rounded-md border p-4">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{rule.code}</Badge>
                          <div className="font-medium">{rule.title}</div>
                        </div>
                        <p className="mt-2 text-sm">{rule.direction}</p>
                        <p className="mt-2 text-sm text-muted-foreground">
                          {rule.legal_basis}
                        </p>
                        <p className="mt-2 text-sm text-muted-foreground">
                          Необходимо: {rule.required_evidence.join(", ")}.
                        </p>
                      </div>
                    ))}
              </div>
              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Код</TableHead>
                      <TableHead>Направление</TableHead>
                      <TableHead>Правовая основа</TableHead>
                      <TableHead>Необходимые материалы</TableHead>
                    </TableRow>
                  </TableHeader>
                  {loading ? (
                    <TableLoading columns={4} />
                  ) : (
                    <TableBody>
                      {(data?.rules ?? []).map((rule) => (
                        <TableRow key={rule.code}>
                          <TableCell>
                            <Badge variant="outline">{rule.code}</Badge>
                          </TableCell>
                          <TableCell className="min-w-64 whitespace-normal">
                            <div className="font-medium">{rule.title}</div>
                            <div className="mt-1 text-sm text-muted-foreground">
                              {rule.direction}
                            </div>
                          </TableCell>
                          <TableCell className="min-w-64 whitespace-normal">
                            {rule.legal_basis}
                          </TableCell>
                          <TableCell className="min-w-64 whitespace-normal">
                            {rule.required_evidence.join(", ")}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  )}
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
