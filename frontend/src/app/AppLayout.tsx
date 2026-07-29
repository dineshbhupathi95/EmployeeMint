import {
  BarChart3,
  Building2,
  Calendar,
  CheckSquare,
  ChevronDown,
  ClipboardList,
  Clock,
  FileText,
  LayoutDashboard,
  LogOut,
  Settings,
  UserPlus,
  Users,
  Wallet,
  UserCheck,
} from "lucide-react";
import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { TopBar } from "@/components/TopBar";
import { AnnouncementTicker } from "@/components/AnnouncementTicker";
import { useModuleVisible } from "@/hooks/usePermission";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

type NavItemConfig = {
  path: string;
  label: string;
  icon: typeof LayoutDashboard;
  module: string;
};

type NavGroupConfig = {
  label: string;
  icon: typeof LayoutDashboard;
  module: string;
  children: NavItemConfig[];
};

const NAV_ITEMS: NavItemConfig[] = [
  { path: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard, module: "dashboard" },
  { path: "/app/employees", label: "Employees", icon: Users, module: "employee" },
  { path: "/app/attendance", label: "Attendance", icon: Clock, module: "attendance" },
  { path: "/app/leave", label: "Leave", icon: Calendar, module: "leave" },
  { path: "/app/timesheets", label: "Timesheets", icon: ClipboardList, module: "timesheets" },
  { path: "/app/finance", label: "My Pay", icon: Wallet, module: "finance" },
  { path: "/app/approvals", label: "Approvals", icon: CheckSquare, module: "approvals" },
  { path: "/app/organization", label: "Organization", icon: Building2, module: "organization" },
  { path: "/app/my-team", label: "My Team", icon: UserCheck, module: "myteam" },
  { path: "/app/reports", label: "Reports", icon: BarChart3, module: "reports" },
];

const HR_LIFECYCLE_GROUP: NavGroupConfig = {
  label: "HR Lifecycle",
  icon: UserPlus,
  module: "hr_lifecycle",
  children: [
    { path: "/app/hr-lifecycle", label: "Overview", icon: UserPlus, module: "hr_lifecycle" },
    { path: "/app/onboarding", label: "Onboarding", icon: UserPlus, module: "onboarding" },
    { path: "/app/offboarding", label: "Offboarding", icon: LogOut, module: "offboarding" },
    { path: "/app/offer-letters", label: "Offer Letters", icon: FileText, module: "offer_letters" },
  ],
};

function NavItem({
  item,
  active,
  nested = false,
}: {
  item: NavItemConfig;
  active: boolean;
  nested?: boolean;
}) {
  const visible = useModuleVisible(item.module);
  if (!visible) return null;
  const Icon = item.icon;
  return (
    <Link
      to={item.path}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        nested && "pl-9",
        active
          ? "bg-brand-600 text-white"
          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
      )}
    >
      <Icon className="h-4 w-4" />
      {item.label}
    </Link>
  );
}

function NavGroup({ group }: { group: NavGroupConfig }) {
  const location = useLocation();
  const groupVisible = useModuleVisible(group.module);
  const [open, setOpen] = useState(() =>
    group.children.some((child) => location.pathname.startsWith(child.path)),
  );

  if (!groupVisible) return null;

  const isActive = group.children.some((child) => location.pathname.startsWith(child.path));
  const Icon = group.icon;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-brand-50 text-brand-700"
            : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
        )}
      >
        <Icon className="h-4 w-4" />
        <span className="flex-1 text-left">{group.label}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="mt-1 space-y-1">
          {group.children.map((child) => (
            <NavItem
              key={child.path}
              item={child}
              nested
              active={location.pathname.startsWith(child.path)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function AppLayout() {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const settingsVisible = useModuleVisible("settings");

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex h-full w-64 shrink-0 flex-col border-r-4 border-brand-600 bg-white transition-colors">
        <div className="shrink-0 border-b border-brand-100 bg-brand-50 p-6 transition-colors">
          <h1 className="text-lg font-bold text-brand-700 transition-colors">EmployeeMint</h1>
          {user?.tenant_slug && (
            <p className="mt-1 text-xs text-slate-500">{user.tenant_slug}</p>
          )}
        </div>
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-4">
          {NAV_ITEMS.map((item) => (
            <NavItem
              key={item.path}
              item={item}
              active={location.pathname.startsWith(item.path)}
            />
          ))}
          <NavGroup group={HR_LIFECYCLE_GROUP} />
          {settingsVisible && (
            <NavItem
              item={{ path: "/app/settings", label: "Settings", icon: Settings, module: "settings" }}
              active={location.pathname.startsWith("/app/settings")}
            />
          )}
        </nav>
        <div className="shrink-0 border-t border-slate-200 p-4">
          <div className="mb-3 px-3">
            <p className="text-sm font-medium text-slate-900">{user?.full_name || user?.email}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>
      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-slate-50">
        <AnnouncementTicker />
        <TopBar />
        <div className="min-h-0 flex-1 overflow-y-auto">
          {user?.is_impersonation && (
            <div className="bg-amber-100 px-6 py-2 text-center text-sm font-medium text-amber-800">
              You are impersonating this tenant admin (support mode)
            </div>
          )}
          {!user?.is_setup_complete && (
            <div className="bg-brand-50 px-6 py-3 text-center text-sm text-brand-800">
              Setup incomplete —{" "}
              <Link to="/app/setup" className="font-medium underline hover:text-brand-900">
                complete the onboarding wizard
              </Link>{" "}
              to unlock all features.
            </div>
          )}
          <div className="p-4 sm:p-6 lg:p-8">
            <div className="em-page">
              <Outlet />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
