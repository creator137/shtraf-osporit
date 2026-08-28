import { Outlet, Link, useLocation } from "react-router-dom"

import { AppSidebar } from "@/components/app-sidebar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"

function PageBreadcrumb() {
  const location = useLocation()
  const isCaseDetail = /^\/cases\/\d+$/.test(location.pathname)
  const pageName = location.pathname.startsWith("/cases")
    ? "Дела"
    : location.pathname.startsWith("/legal-rules")
      ? "Юридические правила"
      : "Пользователи"

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {isCaseDetail ? (
          <>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to="/cases">Дела</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>Карточка дела</BreadcrumbPage>
            </BreadcrumbItem>
          </>
        ) : (
          <BreadcrumbItem>
            <BreadcrumbPage>{pageName}</BreadcrumbPage>
          </BreadcrumbItem>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

export function AppShell() {
  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger aria-label="Открыть навигацию" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <PageBreadcrumb />
          </header>
          <main className="flex flex-1 flex-col p-4 md:p-6">
            <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col">
              <Outlet />
            </div>
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
