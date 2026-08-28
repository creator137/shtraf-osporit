import { useState } from "react"
import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { FineNoticeForm } from "@/components/fine-notice-form"
import type { FineNoticeItem } from "@/lib/api"
import { emptyFineNotice } from "@/lib/fine-notice"

afterEach(cleanup)

function FormHarness({ onSave }: { onSave: () => Promise<void> }) {
  const [notice, setNotice] = useState<FineNoticeItem>(emptyFineNotice)
  return (
    <FineNoticeForm
      notice={notice}
      original={emptyFineNotice}
      saving={false}
      error={null}
      onChange={setNotice}
      onSave={onSave}
    />
  )
}

describe("FineNoticeForm", () => {
  it("enables confirmation after an operator changes a field", async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(async () => undefined)
    render(<FormHarness onSave={onSave} />)
    const save = screen.getByRole("button", { name: /сохранить и подтвердить/i })

    expect(save).toHaveProperty("disabled", true)
    await user.type(screen.getByLabelText("Номер постановления"), "188101")
    expect(save).toHaveProperty("disabled", false)
    await user.click(save)

    expect(onSave).toHaveBeenCalledOnce()
  })

  it("rejects a fractional fine amount before sending it", async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(async () => undefined)
    render(<FormHarness onSave={onSave} />)

    await user.type(screen.getByLabelText("Сумма штрафа, руб."), "12.5")
    await user.click(
      screen.getByRole("button", { name: /сохранить и подтвердить/i })
    )

    expect(onSave).not.toHaveBeenCalled()
    expect(
      screen.getByText("Сумма штрафа должна быть целым неотрицательным числом.")
    ).toBeTruthy()
  })
})
