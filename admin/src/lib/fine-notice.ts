import type { FineNoticeItem } from "@/lib/api"

export const emptyFineNotice: FineNoticeItem = {
  notice_number: null,
  notice_date: null,
  uin: null,
  fine_amount: null,
  article: null,
  vehicle_plate: null,
  violation_datetime: null,
  violation_place: null,
  issuing_authority: null,
}

export function hasNoticeChanges(
  notice: FineNoticeItem,
  original: FineNoticeItem
) {
  return JSON.stringify(notice) !== JSON.stringify(original)
}
