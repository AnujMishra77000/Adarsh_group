import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";

import { AppShell } from "@/layouts/AppShell";
import { AuthLayout } from "@/layouts/AuthLayout";
import { CRM_PATHS, crmPath } from "@/lib/routes";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { ShopRoute } from "@/routes/ShopRoute";

const AnalyticsPage = lazy(() =>
  import("@/pages/analytics/AnalyticsPage").then((module) => ({ default: module.AnalyticsPage }))
);
const AdminRegisterPage = lazy(() =>
  import("@/pages/auth/AdminRegisterPage").then((module) => ({ default: module.AdminRegisterPage }))
);
const ShopEntryPage = lazy(() => import("@/pages/auth/ShopEntryPage").then((module) => ({ default: module.ShopEntryPage })));
const ShopResolvePage = lazy(() =>
  import("@/pages/auth/ShopResolvePage").then((module) => ({ default: module.ShopResolvePage }))
);
const LaunchPage = lazy(() => import("@/pages/auth/LaunchPage").then((module) => ({ default: module.LaunchPage })));
const LandingPage = lazy(() => import("@/pages/auth/LandingPage").then((module) => ({ default: module.LandingPage })));
const LoginPage = lazy(() => import("@/pages/auth/LoginPage").then((module) => ({ default: module.LoginPage })));

const BillingPage = lazy(() => import("@/pages/billing/BillingPage").then((module) => ({ default: module.BillingPage })));
const BillingRecordsPage = lazy(() =>
  import("@/pages/billing/BillingRecordsPage").then((module) => ({ default: module.BillingRecordsPage }))
);
const BillingDetailPage = lazy(() =>
  import("@/pages/billing/BillingDetailPage").then((module) => ({ default: module.BillingDetailPage }))
);
const BillingEditPage = lazy(() =>
  import("@/pages/billing/BillingEditPage").then((module) => ({ default: module.BillingEditPage }))
);

const CampaignsPage = lazy(() =>
  import("@/pages/campaigns/CampaignsPage").then((module) => ({ default: module.CampaignsPage }))
);
const SharedChatPage = lazy(() =>
  import("@/pages/chat/SharedChatPage").then((module) => ({ default: module.SharedChatPage }))
);

const CustomersPage = lazy(() =>
  import("@/pages/customers/CustomersPage").then((module) => ({ default: module.CustomersPage }))
);
const CustomerRecordsPage = lazy(() =>
  import("@/pages/customers/CustomerRecordsPage").then((module) => ({ default: module.CustomerRecordsPage }))
);

const DashboardPage = lazy(() =>
  import("@/pages/dashboard/DashboardPage").then((module) => ({ default: module.DashboardPage }))
);

const PrescriptionsPage = lazy(() =>
  import("@/pages/prescriptions/PrescriptionsPage").then((module) => ({ default: module.PrescriptionsPage }))
);
const PrescriptionsRecordsPage = lazy(() =>
  import("@/pages/prescriptions/PrescriptionsRecordsPage").then((module) => ({ default: module.PrescriptionsRecordsPage }))
);

const StaffManagementPage = lazy(() =>
  import("@/pages/staff/StaffManagementPage").then((module) => ({ default: module.StaffManagementPage }))
);

const VendorsPage = lazy(() => import("@/pages/vendors/VendorsPage").then((module) => ({ default: module.VendorsPage })));
const VisitWorkspacePage = lazy(() =>
  import("@/pages/visits/VisitWorkspacePage").then((module) => ({ default: module.VisitWorkspacePage }))
);

const routeFallback = (
  <div className="rounded-xl border border-pink-300/25 bg-matte-850/90 px-4 py-6 text-sm text-slate-200 shadow-neon-ring">
    Loading module...
  </div>
);

function renderLazyPage(element: ReactNode) {
  return <Suspense fallback={routeFallback}>{element}</Suspense>;
}

function LegacyShopRedirect() {
  const params = useParams<{ shopKey: string }>();
  return <Navigate to={`${CRM_PATHS.shopResolver}/${params.shopKey ?? ""}`} replace />;
}

function LegacyCrmRedirect() {
  const location = useLocation();
  return <Navigate to={crmPath(location.pathname + location.search)} replace />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to={CRM_PATHS.root} replace />} />

      <Route path="/landing" element={<Navigate to={CRM_PATHS.landing} replace />} />
      <Route path="/shop-entry" element={<Navigate to={CRM_PATHS.shopEntry} replace />} />
      <Route path="/shop/:shopKey" element={<LegacyShopRedirect />} />
      <Route path="/login" element={<Navigate to={CRM_PATHS.loginAdmin} replace />} />
      <Route path="/login/admin" element={<Navigate to={CRM_PATHS.loginAdmin} replace />} />
      <Route path="/login/staff" element={<Navigate to={CRM_PATHS.loginStaff} replace />} />
      <Route path="/admin-register" element={<Navigate to={CRM_PATHS.adminRegister} replace />} />
      <Route path="/dashboard" element={<Navigate to={CRM_PATHS.dashboard} replace />} />
      <Route path="/customers/*" element={<LegacyCrmRedirect />} />
      <Route path="/visits/*" element={<LegacyCrmRedirect />} />
      <Route path="/prescriptions/*" element={<LegacyCrmRedirect />} />
      <Route path="/vendors/*" element={<LegacyCrmRedirect />} />
      <Route path="/billing/*" element={<LegacyCrmRedirect />} />
      <Route path="/campaigns/*" element={<LegacyCrmRedirect />} />
      <Route path="/shared-chat" element={<Navigate to={CRM_PATHS.sharedChat} replace />} />
      <Route path="/analytics" element={<Navigate to={CRM_PATHS.analytics} replace />} />
      <Route path="/staff-management" element={<Navigate to={CRM_PATHS.staffManagement} replace />} />

      <Route path={CRM_PATHS.root} element={renderLazyPage(<LaunchPage />)} />
      <Route path={CRM_PATHS.landing} element={renderLazyPage(<ShopRoute><LandingPage /></ShopRoute>)} />
      <Route path={CRM_PATHS.shopEntry} element={renderLazyPage(<ShopEntryPage />)} />
      <Route path={`${CRM_PATHS.shopResolver}/:shopKey`} element={renderLazyPage(<ShopResolvePage />)} />

      <Route element={<ShopRoute><AuthLayout /></ShopRoute>}>
        <Route path={CRM_PATHS.login} element={<Navigate to={CRM_PATHS.loginAdmin} replace />} />
        <Route path={CRM_PATHS.loginAdmin} element={renderLazyPage(<LoginPage mode="admin" />)} />
        <Route path={CRM_PATHS.loginStaff} element={renderLazyPage(<LoginPage mode="staff" />)} />
        <Route path={CRM_PATHS.adminRegister} element={renderLazyPage(<AdminRegisterPage />)} />
      </Route>

      <Route
        element={<ShopRoute><ProtectedRoute><AppShell /></ProtectedRoute></ShopRoute>}
      >
        <Route path={CRM_PATHS.dashboard} element={renderLazyPage(<DashboardPage />)} />

        <Route path={CRM_PATHS.customers} element={renderLazyPage(<CustomersPage />)} />
        <Route path={CRM_PATHS.customerRecords} element={renderLazyPage(<CustomerRecordsPage />)} />
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={renderLazyPage(<VisitWorkspacePage />)} />

        <Route path={CRM_PATHS.prescriptions} element={renderLazyPage(<PrescriptionsPage />)} />
        <Route path={CRM_PATHS.prescriptionRecords} element={renderLazyPage(<PrescriptionsRecordsPage />)} />

        <Route path={CRM_PATHS.vendors} element={renderLazyPage(<VendorsPage />)} />

        <Route path={CRM_PATHS.billing} element={renderLazyPage(<BillingPage />)} />
        <Route path={CRM_PATHS.billingRecords} element={renderLazyPage(<BillingRecordsPage />)} />
        <Route path={`${CRM_PATHS.billing}/view/:billId`} element={renderLazyPage(<BillingDetailPage />)} />
        <Route
          path={`${CRM_PATHS.billing}/edit/:billId`}
          element={<ProtectedRoute allowedRoles={["admin", "staff"]}>{renderLazyPage(<BillingEditPage />)}</ProtectedRoute>}
        />

        <Route path={CRM_PATHS.campaigns} element={renderLazyPage(<CampaignsPage />)} />
        <Route path={CRM_PATHS.sharedChat} element={renderLazyPage(<SharedChatPage />)} />

        <Route
          path={CRM_PATHS.analytics}
          element={<ProtectedRoute allowedRoles={["admin"]}>{renderLazyPage(<AnalyticsPage />)}</ProtectedRoute>}
        />
        <Route
          path={CRM_PATHS.staffManagement}
          element={<ProtectedRoute allowedRoles={["admin"]}>{renderLazyPage(<StaffManagementPage />)}</ProtectedRoute>}
        />
      </Route>

      <Route path="*" element={<Navigate to={CRM_PATHS.root} replace />} />
    </Routes>
  );
}
