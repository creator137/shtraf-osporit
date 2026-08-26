import { BriefcaseBusinessIcon, UsersIcon } from "lucide-react"
import { NavLink, useLocation } from "react-router-dom"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

const navigation = [
  { label: "Пользователи", path: "/users", icon: UsersIcon },
  { label: "Дела", path: "/cases", icon: BriefcaseBusinessIcon },
]

export function AppSidebar() {
  const location = useLocation()

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader className="border-b px-4 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
            ШО
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">Штраф.Оспорить</div>
            <div className="truncate text-xs text-muted-foreground">
              Админ-панель
            </div>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigation.map((item) => (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname.startsWith(item.path)}
                    tooltip={item.label}
                  >
                    <NavLink to={item.path}>
                      <item.icon />
                      <span>{item.label}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
