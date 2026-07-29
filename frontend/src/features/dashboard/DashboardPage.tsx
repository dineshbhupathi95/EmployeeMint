import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  Calendar,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock,
  ClipboardList,
  PartyPopper,
  Pin,
  Users,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { Can } from "@/components/Can";
import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { useAnyPermission, usePermission } from "@/hooks/usePermission";

interface DashboardSummary {
  pending_approvals: number;
  leave_balances: {
    leave_type_id: string;
    leave_type_name: string;
    available: number | string;
    used: number | string;
    allocated: number | string;
    pending: number | string;
  }[];
  attendance_today: {
    checked_in: boolean;
    checked_out: boolean;
    mode: string;
    check_in: string | null;
    check_out: string | null;
  } | null;
  team_present: number;
  team_total: number;
  announcements: { id: string; title: string; body: string; is_pinned: boolean }[];
  upcoming_holidays: { id: string; name: string; date: string; is_optional: boolean; weekday: string }[];
  upcoming_birthdays: { id: string; name: string; date: string; days_until: number }[];
  my_pending_leave: number;
  my_approved_leave_this_year: number;
  unread_notifications: number;
  timesheet_drafts: number;
  timesheet_pending: number;
  headcount: number;
  present_today_org: number;
}

function num(v: number | string | null | undefined) {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? 0));
  return Number.isFinite(n) ? n : 0;
}

function formatTime(iso: string | null | undefined) {
  if (!iso) return null;
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatHolidayDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function MetricCard({
  to,
  label,
  value,
  hint,
  icon: Icon,
  tone = "brand",
}: {
  to?: string;
  label: string;
  value: string | number;
  hint: string;
  icon: typeof Clock;
  tone?: "brand" | "emerald" | "amber" | "slate";
}) {
  const tones = {
    brand: "bg-brand-50 text-brand-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    slate: "bg-slate-100 text-slate-700",
  };
  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 break-words text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            {value}
          </p>
          <p className="mt-1 text-xs text-slate-400">{hint}</p>
        </div>
        <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", tones[tone])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </>
  );

  const className = cn(
    "block h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow",
    to && "hover:shadow-md",
  );

  return to ? (
    <Link to={to} className={className}>
      {inner}
    </Link>
  ) : (
    <div className={className}>{inner}</div>
  );
}

export function DashboardPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const canApprovals = useAnyPermission(["approvals.view", "approvals.action"]);
  const canLeave = useAnyPermission(["leave.view.own", "leave.apply"]);
  const canAttendance = usePermission("attendance.mark.own");
  const canTeam = usePermission("employee.view.team");
  const canTimesheet = usePermission("timesheet.submit");
  const canOrgMetrics = useAnyPermission(["employee.view.all", "reports.view"]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () =>
      apiRequest<DashboardSummary>("/api/v1/dashboard/summary", { token: accessToken }),
  });

  const leaveAvailable =
    data?.leave_balances.reduce((s, b) => s + num(b.available), 0) ?? 0;
  const firstName = user?.full_name?.split(" ")[0];
  const todayLabel = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const attendanceLabel = !data?.attendance_today?.checked_in
    ? "Not in"
    : data.attendance_today.checked_out
      ? "Done"
      : "Checked in";

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-slate-50 px-6 py-7 sm:px-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-brand-100/60 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-20 right-20 h-40 w-40 rounded-full bg-brand-200/40 blur-2xl" />
        <div className="relative flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-brand-700">{greeting()}</p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
              {firstName ? `${firstName}` : "Welcome back"}
            </h1>
            <p className="mt-2 text-slate-500">{todayLabel} · Here&apos;s your workplace snapshot</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(data?.unread_notifications ?? 0) > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm ring-1 ring-slate-200">
                <Bell className="h-3.5 w-3.5 text-brand-600" />
                {data!.unread_notifications} unread
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm ring-1 ring-slate-200">
              <CalendarDays className="h-3.5 w-3.5 text-brand-600" />
              {data?.upcoming_holidays?.length ?? 0} upcoming holidays
            </span>
          </div>
        </div>
      </section>

      {isLoading && <p className="text-sm text-slate-500">Loading dashboard...</p>}
      {isError && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load dashboard{error instanceof Error ? `: ${error.message}` : "."}
        </p>
      )}

      <section className="grid auto-rows-fr grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {canAttendance && (
          <MetricCard
            to="/app/attendance"
            label="Attendance Today"
            value={attendanceLabel}
            hint={
              data?.attendance_today?.checked_in
                ? `${formatTime(data.attendance_today.check_in) ?? ""}${data.attendance_today.check_out ? ` → ${formatTime(data.attendance_today.check_out)}` : ""} · ${data.attendance_today.mode.replace(/_/g, " ")}`
                : "Tap to check in"
            }
            icon={Clock}
            tone={data?.attendance_today?.checked_in ? "emerald" : "amber"}
          />
        )}
        {canLeave && (
          <MetricCard
            to="/app/leave"
            label="Leave Available"
            value={leaveAvailable.toFixed(1)}
            hint={`${data?.my_pending_leave ?? 0} pending · ${data?.my_approved_leave_this_year ?? 0} approved this year`}
            icon={Calendar}
            tone="brand"
          />
        )}
        {canApprovals && (
          <MetricCard
            to="/app/approvals"
            label="Pending Approvals"
            value={data?.pending_approvals ?? 0}
            hint="Awaiting your action"
            icon={CheckCircle2}
            tone={(data?.pending_approvals ?? 0) > 0 ? "amber" : "emerald"}
          />
        )}
        {canTeam && (
          <MetricCard
            to="/app/my-team"
            label="Team Present"
            value={data ? `${data.team_present}/${data.team_total}` : "—"}
            hint="Checked in today"
            icon={Users}
            tone="slate"
          />
        )}
        {canTimesheet && (
          <MetricCard
            to="/app/timesheets"
            label="Timesheets"
            value={(data?.timesheet_drafts ?? 0) + (data?.timesheet_pending ?? 0)}
            hint={`${data?.timesheet_drafts ?? 0} draft · ${data?.timesheet_pending ?? 0} pending`}
            icon={ClipboardList}
            tone="brand"
          />
        )}
        {canOrgMetrics && (
          <MetricCard
            to="/app/reports"
            label="Org Headcount"
            value={data?.headcount ?? 0}
            hint={`${data?.present_today_org ?? 0} present today`}
            icon={Users}
            tone="emerald"
          />
        )}
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {canLeave && (
          <Card className="min-w-0 h-full">
            <CardHeader title="Leave balances" description="By leave type" />
            <div className="space-y-4">
              {data?.leave_balances?.length ? (
                data.leave_balances.map((b) => {
                  const available = num(b.available);
                  const allocated = num(b.allocated);
                  const used = num(b.used);
                  const pending = num(b.pending);
                  const pct = allocated > 0 ? Math.min(100, (available / allocated) * 100) : 0;
                  return (
                    <div key={b.leave_type_id}>
                      <div className="mb-1.5 flex items-center justify-between gap-2 text-sm">
                        <span className="truncate font-medium text-slate-800">{b.leave_type_name}</span>
                        <span className="shrink-0 tabular-nums text-slate-500">
                          {available.toFixed(1)} / {allocated}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-brand-600 transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <p className="mt-1 text-[11px] text-slate-400">
                        Used {used} · Pending {pending}
                      </p>
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-slate-500">No leave balances yet.</p>
              )}
            </div>
            <Link
              to="/app/leave"
              className="mt-4 inline-flex items-center text-sm font-medium text-brand-700 hover:underline"
            >
              Manage leave <ChevronRight className="ml-1 h-4 w-4" />
            </Link>
          </Card>
        )}

        <Card className="min-w-0 h-full">
          <CardHeader title="Upcoming holidays" description="Next 90 days" />
          {data?.upcoming_holidays?.length ? (
            <ul className="space-y-3">
              {data.upcoming_holidays.map((h) => (
                <li
                  key={h.id}
                  className="flex items-center gap-3 rounded-lg border border-slate-100 px-3 py-2.5"
                >
                  <div className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-lg bg-brand-50 text-brand-800">
                    <span className="text-[10px] font-semibold uppercase leading-none">{h.weekday}</span>
                    <span className="mt-0.5 text-sm font-bold leading-none">
                      {formatHolidayDate(h.date).split(" ")[0]}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-900">{h.name}</p>
                    <p className="text-xs text-slate-500">
                      {formatHolidayDate(h.date)}
                      {h.is_optional ? " · Optional" : ""}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No holidays in the next 90 days. Add them in Settings.</p>
          )}
        </Card>

        <div className="min-w-0 space-y-6 lg:col-span-2 xl:col-span-1">
          <Card>
            <CardHeader title="Quick actions" />
            <div className="grid grid-cols-2 gap-2">
              <Can permission="leave.apply">
                <Link to="/app/leave" className="rounded-xl border border-slate-200 px-3 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800">
                  Apply leave
                </Link>
              </Can>
              <Can permission="attendance.mark.own">
                <Link to="/app/attendance" className="rounded-xl border border-slate-200 px-3 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800">
                  Attendance
                </Link>
              </Can>
              <Can permission="timesheet.submit">
                <Link to="/app/timesheets" className="rounded-xl border border-slate-200 px-3 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800">
                  Log hours
                </Link>
              </Can>
              <Can permission="payroll.view.own">
                <Link to="/app/finance" className="rounded-xl border border-slate-200 px-3 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800">
                  <span className="inline-flex items-center gap-1"><Wallet className="h-3.5 w-3.5" /> My Pay</span>
                </Link>
              </Can>
              <Can permission="approvals.view">
                <Link to="/app/approvals" className="rounded-xl border border-slate-200 px-3 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800">
                  Approvals
                </Link>
              </Can>
              <Can permission="reimbursement.submit">
                <Link to="/app/finance" className="rounded-xl border border-slate-200 px-3 py-3 text-sm font-medium text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800">
                  Expense claim
                </Link>
              </Can>
            </div>
          </Card>

          {(data?.upcoming_birthdays?.length ?? 0) > 0 && (
            <Card>
              <CardHeader title="Birthdays" description="Next 30 days" />
              <ul className="space-y-2">
                {data!.upcoming_birthdays.map((b) => (
                  <li key={b.id} className="flex items-center justify-between text-sm">
                    <span className="inline-flex items-center gap-2 font-medium text-slate-800">
                      <PartyPopper className="h-3.5 w-3.5 text-amber-500" />
                      {b.name}
                    </span>
                    <span className="text-xs text-slate-500">
                      {b.days_until === 0 ? "Today" : `in ${b.days_until}d`}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>

      <Card className="min-w-0">
        <CardHeader title="Announcements" description="Company-wide updates (managed in Settings)" />
        {data?.announcements?.length ? (
          <ul className="divide-y divide-slate-100">
            {data.announcements.map((a) => (
              <li key={a.id} className="flex gap-3 py-4 first:pt-0 last:pb-0">
                <div className={cn(
                  "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                  a.is_pinned ? "bg-amber-50 text-amber-600" : "bg-slate-50 text-slate-400",
                )}>
                  <Pin className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-slate-900">
                    {a.title}
                    {a.is_pinned && (
                      <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-amber-800">
                        Pinned
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-sm text-slate-500 line-clamp-2">{a.body}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">
            No announcements on the dashboard. Publish one in Settings → Announcements and keep it set to Show.
          </p>
        )}
      </Card>
    </div>
  );
}
