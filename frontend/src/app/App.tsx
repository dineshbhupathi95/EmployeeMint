import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/app/AppLayout";
import { ThemeProvider } from "@/app/ThemeProvider";
import { ProtectedRoute } from "@/app/ProtectedRoute";
import { LeavePage } from "@/features/leave/LeavePage";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { FinancePage } from "@/features/finance/FinancePage";
import { ApprovalsPage } from "@/features/approvals/ApprovalsPage";
import { OrganizationPage } from "@/features/organization/OrganizationPage";
import { MyTeamPage } from "@/features/myteam/MyTeamPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { EmployeesPage } from "@/features/employees/EmployeesPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { OfferLettersPage } from "@/features/offerletters/OfferLettersPage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { OffboardingPage } from "@/features/offboarding/OffboardingPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { CreateTenantPage } from "@/features/platform/CreateTenantPage";
import { PlatformLoginPage } from "@/features/platform/PlatformLoginPage";
import { PlatformTenantsPage } from "@/features/platform/PlatformTenantsPage";
import { TenantDetailPage } from "@/features/platform/TenantDetailPage";
import { TenantRouteGuard } from "@/app/TenantRouteGuard";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { SetupWizardPage } from "@/features/setup/SetupWizardPage";
import { TimesheetsPage } from "@/features/timesheets/TimesheetsPage";
import { HRLifecyclePage } from "@/features/hrlifecycle/HRLifecyclePage";
import { AssistantPage } from "@/features/assistant/AssistantPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export function App() {
  return (
    <ThemeProvider>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/platform/login" element={<PlatformLoginPage />} />

          <Route element={<ProtectedRoute platform />}>
            <Route path="/platform/tenants" element={<PlatformTenantsPage />} />
            <Route path="/platform/tenants/new" element={<CreateTenantPage />} />
            <Route path="/platform/tenants/:tenantId" element={<TenantDetailPage />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route path="/app/setup" element={<SetupWizardPage />} />
            <Route element={<TenantRouteGuard />}>
              <Route path="/app" element={<AppLayout />}>
                <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="employees" element={<EmployeesPage />} />
              <Route path="attendance" element={<AttendancePage />} />
              <Route path="leave" element={<LeavePage />} />
              <Route path="finance" element={<FinancePage />} />
              <Route path="approvals" element={<ApprovalsPage />} />
              <Route path="organization" element={<OrganizationPage />} />
              <Route path="my-team" element={<MyTeamPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="timesheets" element={<TimesheetsPage />} />
              <Route path="hr-lifecycle" element={<HRLifecyclePage />} />
              <Route path="onboarding" element={<OnboardingPage />} />
              <Route path="offboarding" element={<OffboardingPage />} />
              <Route path="offer-letters" element={<OfferLettersPage />} />
              <Route path="assistant" element={<AssistantPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
    </ThemeProvider>
  );
}
