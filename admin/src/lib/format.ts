import type { UserSummary } from "@/lib/api"

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
})

export function formatDate(value: string): string {
  return dateFormatter.format(new Date(value))
}

export function formatName(user: UserSummary): string {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || "Не указано"
}

export function formatUsername(username: string | null): string {
  return username ? `@${username}` : "Не указан"
}
