import { useAuthStore } from "@/store/auth";

function permissionMatches(granted: string, required: string): boolean {
  if (granted === "*" || granted === required) return true;
  if (granted.endsWith(".*")) {
    const prefix = granted.slice(0, -2);
    return required === prefix || required.startsWith(`${prefix}.`);
  }
  return false;
}

/** Map nav module keys to permission prefixes that grant access */
const MODULE_PREFIXES: Record<string, string[]> = {
  dashboard: ["dashboard"],
  employee: ["employee"],
  attendance: ["attendance"],
  leave: ["leave"],
  finance: ["payroll", "reimbursement", "finance"],
  approvals: ["approvals"],
  organization: ["org"],
  myteam: ["employee"],
  reports: ["reports"],
  settings: ["settings", "leave.manage", "org.manage_roles", "workflows.manage"],
  onboarding: ["onboarding"],
  offboarding: ["offboarding"],
  timesheets: ["timesheet"],
  hr_lifecycle: ["onboarding", "offboarding", "offer_letter", "recruitment"],
  offer_letters: ["offer_letter"],
  recruitment: ["recruitment"],
  assistant: ["assistant"],
};

export function usePermission(permission: string): boolean {
  const permissions = useAuthStore((s) => s.user?.permissions ?? []);
  return permissions.some((p) => permissionMatches(p, permission));
}

export function useAnyPermission(required: string[]): boolean {
  const permissions = useAuthStore((s) => s.user?.permissions ?? []);
  return required.some((req) => permissions.some((p) => permissionMatches(p, req)));
}

export function useModuleVisible(module: string): boolean {
  const permissions = useAuthStore((s) => s.user?.permissions ?? []);
  if (permissions.includes("*")) return true;

  const prefixes = MODULE_PREFIXES[module] ?? [module];
  return permissions.some((p) =>
    prefixes.some(
      (prefix) => p === prefix || p.startsWith(`${prefix}.`) || permissionMatches(p, `${prefix}.view`),
    ),
  );
}
