import { Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "@/components/app-shell"
import { CaseDetailPage } from "@/pages/case-detail-page"
import { CasesPage } from "@/pages/cases-page"
import { UsersPage } from "@/pages/users-page"
import { LegalRulesPage } from "@/pages/legal-rules-page"
import { PaymentIntentsPage } from "@/pages/payment-intents-page"

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/users" replace />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/:caseId" element={<CaseDetailPage />} />
        <Route path="legal-rules" element={<LegalRulesPage />} />
        <Route path="payment-intents" element={<PaymentIntentsPage />} />
        <Route path="*" element={<Navigate to="/users" replace />} />
      </Route>
    </Routes>
  )
}
