import {
  BarChart3,
  Building2,
  Calendar,
  CheckSquare,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
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
import { useEffect, useRef, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { TopBar } from "@/components/TopBar";
import { AnnouncementTicker } from "@/components/AnnouncementTicker";
import { OrgBrand } from "@/components/OrgBrand";
import { useModuleVisible, useAnyPermission } from "@/hooks/usePermission";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const SIDEBAR_COLLAPSED_KEY = "employeemint-sidebar-collapsed";

type NavItemConfig = {
  path: string;
  label: string;
  icon: typeof LayoutDashboard;
  module: string;
  requiredPermissions?: string[];
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
  { path: "/app/payroll", label: "Payroll Runs", icon: FileText, module: "finance", requiredPermissions: ["payroll.draft", "payroll.submit", "payroll.approve", "payroll.view.all", "payroll.process", "payroll.export", "payroll.finalize", "settings.manage"] },
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
    { path: "/app/recruitment", label: "Recruitment", icon: Users, module: "recruitment" },
    { path: "/app/offboarding", label: "Offboarding", icon: LogOut, module: "offboarding" },
    { path: "/app/offer-letters", label: "Offer Letters", icon: FileText, module: "offer_letters" },
  ],
};

function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function NavItem({
  item,
  active,
  nested = false,
  collapsed = false,
}: {
  item: NavItemConfig;
  active: boolean;
  nested?: boolean;
  collapsed?: boolean;
}) {
  const visible = useModuleVisible(item.module);
  const hasRequiredPerms = useAnyPermission(item.requiredPermissions ?? []);
  if (!visible) return null;
  if (item.requiredPermissions?.length && !hasRequiredPerms) return null;
  const Icon = item.icon;
  return (
    <Link
      to={item.path}
      title={collapsed ? item.label : undefined}
      className={cn(
        "flex items-center rounded-lg text-sm font-medium transition-colors",
        collapsed ? "justify-center p-2.5" : "gap-3 px-3 py-2",
        nested && !collapsed && "pl-9",
        active
          ? "bg-brand-600 text-white"
          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}

function NavGroup({
  group,
  collapsed = false,
}: {
  group: NavGroupConfig;
  collapsed?: boolean;
}) {
  const location = useLocation();
  const groupVisible = useModuleVisible(group.module);
  const [open, setOpen] = useState(() =>
    group.children.some((child) => location.pathname.startsWith(child.path)),
  );
  const [flyoutOpen, setFlyoutOpen] = useState(false);
  const flyoutRef = useRef<HTMLDivElement>(null);

  const isActive = group.children.some((child) => location.pathname.startsWith(child.path));
  const Icon = group.icon;

  useEffect(() => {
    if (!flyoutOpen) return;
    function onPointerDown(e: MouseEvent) {
      if (flyoutRef.current && !flyoutRef.current.contains(e.target as Node)) {
        setFlyoutOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [flyoutOpen]);

  useEffect(() => {
    setFlyoutOpen(false);
  }, [location.pathname]);

  if (!groupVisible) return null;

  if (collapsed) {
    return (
      <div className="relative" ref={flyoutRef}>
        <button
          type="button"
          title={group.label}
          onClick={() => setFlyoutOpen((v) => !v)}
          className={cn(
            "flex w-full items-center justify-center rounded-lg p-2.5 text-sm font-medium transition-colors",
            isActive || flyoutOpen
              ? "bg-brand-600 text-white"
              : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
          )}
        >
          <Icon className="h-4 w-4 shrink-0" />
        </button>
        {flyoutOpen && (
          <div
            className="absolute left-full top-0 z-50 ml-2 min-w-[11rem] rounded-lg border border-slate-200 bg-white p-2 shadow-lg"
          >
            <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {group.label}
            </p>
            <div className="space-y-1">
              {group.children.map((child) => (
                <NavItem
                  key={child.path}
                  item={child}
                  active={location.pathname.startsWith(child.path)}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

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
        <Icon className="h-4 w-4 shrink-0" />
        <span className="flex-1 text-left">{group.label}</span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", open && "rotate-180")} />
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
  const [collapsed, setCollapsed] = useState(readSidebarCollapsed);

  useEffect(() => {
    const prevBody = document.body.style.overflow;
    const prevHtml = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevBody;
      document.documentElement.style.overflow = prevHtml;
    };
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  return (
    <div className="h-dvh overflow-hidden">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex h-dvh flex-col border-r-4 border-brand-600 bg-white transition-[width] duration-200 ease-in-out",
          collapsed ? "w-[4.5rem]" : "w-64",
        )}
      >
        <div
          className={cn(
            "shrink-0 border-b border-brand-100 bg-brand-50 transition-colors",
            collapsed ? "p-3" : "p-5",
          )}
        >
          <div className={cn("flex items-center", collapsed ? "justify-center" : "gap-2")}>
            <OrgBrand
              showSlug={!collapsed}
              iconOnly={collapsed}
              size={collapsed ? "md" : "lg"}
              nameClassName="text-lg"
              className={collapsed ? "justify-center" : undefined}
            />
            {!collapsed && (
              <button
                type="button"
                onClick={toggleCollapsed}
                title="Collapse sidebar"
                className="ml-auto shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-white hover:text-slate-700"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            )}
          </div>
          {collapsed && (
            <button
              type="button"
              onClick={toggleCollapsed}
              title="Expand sidebar"
              className="mt-3 flex w-full items-center justify-center rounded-lg p-1.5 text-slate-500 hover:bg-white hover:text-slate-700"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          )}
        </div>
        <nav
          className={cn(
            "min-h-0 flex-1 space-y-1 overflow-y-auto overflow-x-hidden overscroll-y-contain",
            collapsed ? "p-2" : "p-4",
          )}
        >
          {NAV_ITEMS.map((item) => (
            <NavItem
              key={item.path}
              item={item}
              collapsed={collapsed}
              active={location.pathname.startsWith(item.path)}
            />
          ))}
          <NavGroup group={HR_LIFECYCLE_GROUP} collapsed={collapsed} />
          {settingsVisible && (
            <NavItem
              item={{ path: "/app/settings", label: "Settings", icon: Settings, module: "settings" }}
              collapsed={collapsed}
              active={location.pathname.startsWith("/app/settings")}
            />
          )}
        </nav>
        <div className={cn("shrink-0 border-t border-slate-200", collapsed ? "p-2" : "p-4")}>
          {!collapsed && (
            <div className="mb-3 px-3">
              <p className="truncate text-sm font-medium text-slate-900">
                {user?.full_name || user?.email}
              </p>
              <p className="truncate text-xs text-slate-500">{user?.email}</p>
            </div>
          )}
          <button
            type="button"
            onClick={logout}
            title={collapsed ? "Logout" : undefined}
            className={cn(
              "flex w-full items-center rounded-lg text-sm text-slate-600 hover:bg-slate-50",
              collapsed ? "justify-center p-2.5" : "gap-3 px-3 py-2",
            )}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!collapsed && "Logout"}
          </button>
        </div>
      </aside>
      <main
        className={cn(
          "flex h-dvh min-w-0 flex-col bg-slate-50 transition-[margin-left] duration-200 ease-in-out",
          collapsed ? "ml-[4.5rem]" : "ml-64",
        )}
      >
        <AnnouncementTicker />
        <TopBar />
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
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
