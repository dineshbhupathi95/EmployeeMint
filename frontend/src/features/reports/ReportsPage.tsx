import { useMutation, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import type { ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiDownload, apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface NamedValue {
  name: string;
  value: number;
}

interface AttendanceTrendPoint {
  date: string;
  label: string;
  present: number;
  records: number;
}

interface ReportsAnalytics {
  summary: {
    headcount: number;
    pending_leave_requests: number;
    present_today: number;
    approved_leave_requests: number;
    absent_today: number;
  };
  headcount_by_department: NamedValue[];
  employment_status: NamedValue[];
  leave_by_status: NamedValue[];
  leave_by_type: NamedValue[];
  attendance_trend: AttendanceTrendPoint[];
  attendance_by_mode: NamedValue[];
  attendance_today: NamedValue[];
}

const CHART_COLORS = [
  "#2563eb",
  "#059669",
  "#d97706",
  "#7c3aed",
  "#e11d48",
  "#0891b2",
  "#65a30d",
  "#db2777",
];

const STATUS_COLORS: Record<string, string> = {
  Pending: "#d97706",
  Approved: "#059669",
  Rejected: "#e11d48",
  Cancelled: "#94a3b8",
  Present: "#059669",
  "Not checked in": "#cbd5e1",
  Active: "#2563eb",
};

function colorFor(name: string, index: number) {
  return STATUS_COLORS[name] ?? CHART_COLORS[index % CHART_COLORS.length];
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-64 items-center justify-center text-sm text-slate-400">
      {message}
    </div>
  );
}

function ChartPanel({
  title,
  description,
  className,
  children,
}: {
  title: string;
  description?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn("min-w-0", className)}>
      <div className="mb-4">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {children}
    </section>
  );
}

function MetricStrip({
  items,
}: {
  items: { label: string; value: number | string; hint: string }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4 border-y border-slate-200 py-5 sm:grid-cols-4">
      {items.map((item) => (
        <div key={item.label}>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{item.label}</p>
          <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{item.value}</p>
          <p className="mt-0.5 text-xs text-slate-400">{item.hint}</p>
        </div>
      ))}
    </div>
  );
}

const tooltipStyle = {
  borderRadius: 8,
  border: "1px solid #e2e8f0",
  boxShadow: "none",
  fontSize: 12,
};

export function ReportsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["reports-analytics"],
    queryFn: () => apiRequest<ReportsAnalytics>("/api/v1/reports/analytics", { token: accessToken }),
  });

  const exportMutation = useMutation({
    mutationFn: async () => {
      const blob = await apiDownload("/api/v1/reports/export", accessToken);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `employeemint-report-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const summary = data?.summary;
  const presentRate =
    summary && summary.headcount > 0
      ? Math.round((summary.present_today / summary.headcount) * 100)
      : 0;

  return (
    <div className="space-y-10">
      <PageHeader
        title="Reports"
        description="Workforce analytics — attendance, leave, and headcount"
        action={
          <Button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
            <Download className="mr-2 h-4 w-4" />
            {exportMutation.isPending ? "Exporting..." : "Export CSV"}
          </Button>
        }
      />

      {isLoading && <p className="text-sm text-slate-500">Loading analytics...</p>}
      {isError && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load reports{error instanceof Error ? `: ${error.message}` : "."}
        </p>
      )}

      {data && summary && (
        <>
          <MetricStrip
            items={[
              { label: "Headcount", value: summary.headcount, hint: "Active employees" },
              {
                label: "Present today",
                value: `${summary.present_today}`,
                hint: `${presentRate}% of headcount`,
              },
              {
                label: "Pending leave",
                value: summary.pending_leave_requests,
                hint: "Awaiting approval",
              },
              {
                label: "Approved leave",
                value: summary.approved_leave_requests,
                hint: "All-time approved",
              },
            ]}
          />

          <div className="grid gap-10 lg:grid-cols-5">
            <ChartPanel
              className="lg:col-span-3"
              title="Attendance trend"
              description="Checked-in employees over the last 14 days"
            >
              {data.attendance_trend.some((d) => d.present > 0 || d.records > 0) ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.attendance_trend} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                      <defs>
                        <linearGradient id="presentFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#2563eb" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="#2563eb" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        width={36}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Area
                        type="monotone"
                        dataKey="present"
                        name="Present"
                        stroke="#2563eb"
                        strokeWidth={2}
                        fill="url(#presentFill)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyChart message="No attendance records in the last 14 days" />
              )}
            </ChartPanel>

            <ChartPanel
              className="lg:col-span-2"
              title="Today’s attendance"
              description="Present vs not checked in"
            >
              {summary.headcount > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.attendance_today}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={58}
                        outerRadius={88}
                        paddingAngle={2}
                      >
                        {data.attendance_today.map((entry, i) => (
                          <Cell key={entry.name} fill={colorFor(entry.name, i)} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyChart message="No active employees to chart" />
              )}
            </ChartPanel>
          </div>

          <div className="grid gap-10 lg:grid-cols-2">
            <ChartPanel
              title="Headcount by department"
              description="Active employees grouped by department"
            >
              {data.headcount_by_department.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.headcount_by_department}
                      layout="vertical"
                      margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                      <XAxis type="number" allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={100}
                        tick={{ fill: "#475569", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="value" name="Employees" radius={[0, 6, 6, 0]} barSize={18}>
                        {data.headcount_by_department.map((entry, i) => (
                          <Cell key={entry.name} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyChart message="No department headcount data" />
              )}
            </ChartPanel>

            <ChartPanel title="Leave by status" description="All leave requests by approval status">
              {data.leave_by_status.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.leave_by_status}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="48%"
                        outerRadius={90}
                        label={({ name, percent }) =>
                          `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                      >
                        {data.leave_by_status.map((entry, i) => (
                          <Cell key={entry.name} fill={colorFor(entry.name, i)} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyChart message="No leave requests yet" />
              )}
            </ChartPanel>
          </div>

          <div className="grid gap-10 lg:grid-cols-2">
            <ChartPanel title="Leave by type" description="Request volume per leave type">
              {data.leave_by_type.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.leave_by_type} margin={{ top: 8, right: 8, left: -12, bottom: 24 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        interval={0}
                        angle={-20}
                        textAnchor="end"
                        height={50}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        width={36}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="value" name="Requests" fill="#7c3aed" radius={[6, 6, 0, 0]} barSize={36} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyChart message="No leave type data" />
              )}
            </ChartPanel>

            <ChartPanel
              title="Work mode (14 days)"
              description="In-office vs WFH and other attendance modes"
            >
              {data.attendance_by_mode.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.attendance_by_mode} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        width={36}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="value" name="Records" radius={[6, 6, 0, 0]} barSize={40}>
                        {data.attendance_by_mode.map((entry, i) => (
                          <Cell key={entry.name} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyChart message="No attendance mode data" />
              )}
            </ChartPanel>
          </div>

          {data.employment_status.length > 0 && (
            <ChartPanel title="Employment status" description="Workforce by employment status">
              <div className="h-56 w-full max-w-xl">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.employment_status} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="value" name="Employees" radius={[6, 6, 0, 0]} barSize={48}>
                      {data.employment_status.map((entry, i) => (
                        <Cell key={entry.name} fill={colorFor(entry.name, i)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartPanel>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-6">
            <p className="text-sm text-slate-500">
              Download a spreadsheet with summary metrics, employees, leave, and today’s attendance.
            </p>
            <Button variant="secondary" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
              <Download className="mr-2 h-4 w-4" />
              Download report (.csv)
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
