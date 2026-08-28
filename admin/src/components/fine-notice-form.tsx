import { useState } from "react"
import { RotateCcwIcon, SaveIcon, TriangleAlertIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import type { FineNoticeItem } from "@/lib/api"
import { hasNoticeChanges } from "@/lib/fine-notice"

export function FineNoticeForm({
  notice,
  original,
  saving,
  error,
  onChange,
  onSave,
}: {
  notice: FineNoticeItem
  original: FineNoticeItem
  saving: boolean
  error: string | null
  onChange: (notice: FineNoticeItem) => void
  onSave: () => Promise<void>
}) {
  const [validationError, setValidationError] = useState<string | null>(null)
  const dirty = hasNoticeChanges(notice, original)

  function updateField(field: keyof FineNoticeItem, value: string) {
    setValidationError(null)
    onChange({
      ...notice,
      [field]:
        field === "fine_amount"
          ? value === ""
            ? null
            : Number(value)
          : value || null,
    })
  }

  async function submit() {
    if (
      notice.fine_amount !== null &&
      (!Number.isInteger(notice.fine_amount) || notice.fine_amount < 0)
    ) {
      setValidationError("Сумма штрафа должна быть целым неотрицательным числом.")
      return
    }
    setValidationError(null)
    await onSave()
  }

  const fieldError = validationError ?? error

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-1 text-sm font-medium">
          Номер постановления
          <Input
            maxLength={100}
            value={notice.notice_number ?? ""}
            onChange={(event) => updateField("notice_number", event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Дата постановления
          <Input
            maxLength={50}
            placeholder="ДД.ММ.ГГГГ"
            value={notice.notice_date ?? ""}
            onChange={(event) => updateField("notice_date", event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          УИН
          <Input
            maxLength={64}
            value={notice.uin ?? ""}
            onChange={(event) => updateField("uin", event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Сумма штрафа, руб.
          <Input
            type="number"
            min="0"
            step="1"
            value={notice.fine_amount ?? ""}
            onChange={(event) => updateField("fine_amount", event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Статья КоАП
          <Input
            maxLength={255}
            value={notice.article ?? ""}
            onChange={(event) => updateField("article", event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Госномер
          <Input
            maxLength={32}
            value={notice.vehicle_plate ?? ""}
            onChange={(event) => updateField("vehicle_plate", event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Дата и время нарушения
          <Input
            maxLength={100}
            placeholder="ДД.ММ.ГГГГ ЧЧ:ММ"
            value={notice.violation_datetime ?? ""}
            onChange={(event) =>
              updateField("violation_datetime", event.target.value)
            }
          />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Орган
          <Input
            maxLength={1000}
            value={notice.issuing_authority ?? ""}
            onChange={(event) =>
              updateField("issuing_authority", event.target.value)
            }
          />
        </label>
      </div>
      <label className="grid gap-1 text-sm font-medium">
        Место нарушения
        <Textarea
          className="min-h-24"
          maxLength={2000}
          value={notice.violation_place ?? ""}
          onChange={(event) => updateField("violation_place", event.target.value)}
        />
      </label>
      {fieldError ? (
        <Alert variant="destructive">
          <TriangleAlertIcon />
          <AlertTitle>Данные не сохранены</AlertTitle>
          <AlertDescription>{fieldError}</AlertDescription>
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button onClick={submit} disabled={saving || !dirty}>
          <SaveIcon data-icon="inline-start" />
          {saving ? "Сохранение..." : "Сохранить и подтвердить"}
        </Button>
        <Button
          variant="outline"
          onClick={() => onChange(original)}
          disabled={saving || !dirty}
        >
          <RotateCcwIcon data-icon="inline-start" />
          Отменить изменения
        </Button>
      </div>
    </div>
  )
}
