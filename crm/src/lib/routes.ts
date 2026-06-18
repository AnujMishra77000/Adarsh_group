export const CRM_ROOT = "/crm";

export const CRM_PATHS = {
  root: CRM_ROOT,
  shopEntry: `${CRM_ROOT}/shop-entry`,
  shopResolver: `${CRM_ROOT}/shop`,
  landing: `${CRM_ROOT}/landing`,
  login: `${CRM_ROOT}/login`,
  loginAdmin: `${CRM_ROOT}/login/admin`,
  loginStaff: `${CRM_ROOT}/login/staff`,
  adminRegister: `${CRM_ROOT}/admin-register`,
  dashboard: `${CRM_ROOT}/dashboard`,
  customers: `${CRM_ROOT}/customers`,
  customerRecords: `${CRM_ROOT}/customers/records`,
  visitWorkspace: `${CRM_ROOT}/visits`,
  prescriptions: `${CRM_ROOT}/prescriptions`,
  prescriptionRecords: `${CRM_ROOT}/prescriptions/records`,
  vendors: `${CRM_ROOT}/vendors`,
  billing: `${CRM_ROOT}/billing`,
  billingRecords: `${CRM_ROOT}/billing/records`,
  campaigns: `${CRM_ROOT}/campaigns`,
  sharedChat: `${CRM_ROOT}/shared-chat`,
  analytics: `${CRM_ROOT}/analytics`,
  staffManagement: `${CRM_ROOT}/staff-management`
} as const;

export function crmPath(path: string): string {
  if (!path || path === "/") {
    return CRM_ROOT;
  }
  if (path.startsWith(CRM_ROOT + "/") || path === CRM_ROOT) {
    return path;
  }
  return `${CRM_ROOT}${path.startsWith("/") ? path : `/${path}`}`;
}

export function isCrmPath(path: string): boolean {
  return path === CRM_ROOT || path.startsWith(CRM_ROOT + "/");
}
