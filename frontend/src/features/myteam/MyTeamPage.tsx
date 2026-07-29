import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { apiRequest } from "@/api/client";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface TeamMember {
  id: string;
  first_name: string;
  last_name: string;
  employee_code: string;
  work_email: string | null;
  employment_status: string;
  reports_to_employee_id: string | null;
  checked_in_today: boolean;
  checked_out_today: boolean;
  check_in_time: string | null;
  attendance_mode: string | null;
  relation?: "reportee" | "peer";
  manager_name?: string | null;
}

function buildLevels(members: TeamMember[], managerId: string | undefined) {
  if (!managerId) return new Map<string, number>();
  const byId = new Map(members.map((m) => [m.id, m]));
  const levels = new Map<string, number>();

  const getLevel = (id: string): number => {
    if (levels.has(id)) return levels.get(id)!;
    const emp = byId.get(id);
    if (!emp?.reports_to_employee_id || emp.reports_to_employee_id === managerId) {
      levels.set(id, 1);
      return 1;
    }
    if (!byId.has(emp.reports_to_employee_id)) {
      levels.set(id, 1);
      return 1;
    }
    const level = getLevel(emp.reports_to_employee_id) + 1;
    levels.set(id, level);
    return level;
  };

  members.forEach((m) => getLevel(m.id));
  return levels;
}

function formatCheckInTime(iso: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatMode(mode: string | null) {
  if (!mode) return null;
  return mode.replace(/_/g, " ");
}

export function MyTeamPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const managerId = useAuthStore((s) => s.user?.employee_id ?? undefined);

  const { data: team } = useQuery({
    queryKey: ["my-team"],
    queryFn: () => apiRequest<TeamMember[]>("/api/v1/my-team", { token: accessToken }),
    refetchInterval: 60_000,
  });

  const isPeers = (team?.length ?? 0) > 0 && team?.every((m) => m.relation === "peer");

  const levels = useMemo(
    () => (isPeers ? new Map<string, number>() : buildLevels(team ?? [], managerId)),
    [team, managerId, isPeers],
  );

  const directCount = isPeers
    ? 0
    : team?.filter((e) => e.reports_to_employee_id === managerId).length ?? 0;
  const indirectCount = isPeers ? 0 : (team?.length ?? 0) - directCount;
  const checkedInCount = team?.filter((e) => e.checked_in_today).length ?? 0;
  const sharedManager = team?.[0]?.manager_name ?? null;

  const managerName = (id: string | null) => {
    if (!id) return null;
    const mgr = team?.find((e) => e.id === id);
    return mgr ? `${mgr.first_name} ${mgr.last_name}` : null;
  };

  const description = isPeers
    ? `${team?.length ?? 0} teammates under ${sharedManager ?? "your manager"} · ${checkedInCount} checked in today`
    : `${team?.length ?? 0} total · ${directCount} direct · ${indirectCount} indirect · ${checkedInCount} checked in today`;

  return (
    <div className="space-y-6">
      <PageHeader title="My Team" description={description} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {team?.map((e) => {
          const level = levels.get(e.id) ?? 1;
          const reportsTo = isPeers
            ? sharedManager
              ? `Same manager: ${sharedManager}`
              : "Teammate"
            : e.reports_to_employee_id === managerId
              ? "Direct report"
              : managerName(e.reports_to_employee_id);
          const checkInTime = formatCheckInTime(e.check_in_time);
          const mode = formatMode(e.attendance_mode);

          return (
            <Card key={e.id} className={!isPeers && level > 1 ? "border-l-4 border-l-brand-200" : ""}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-900">{e.first_name} {e.last_name}</p>
                  <p className="text-sm text-slate-500">{e.employee_code}</p>
                </div>
                <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {isPeers ? "Peer" : `L${level}`}
                </span>
              </div>

              <div
                className={cn(
                  "mt-3 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
                  e.checked_in_today
                    ? e.checked_out_today
                      ? "border-green-200 bg-green-50 text-green-800"
                      : "border-brand-200 bg-brand-50 text-brand-800"
                    : "border-slate-200 bg-slate-50 text-slate-600",
                )}
              >
                {e.checked_in_today ? (
                  e.checked_out_today ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                  ) : (
                    <Clock className="h-4 w-4 shrink-0 text-brand-600" />
                  )
                ) : (
                  <XCircle className="h-4 w-4 shrink-0 text-slate-400" />
                )}
                <div className="min-w-0">
                  <p className="font-medium">
                    {e.checked_in_today
                      ? e.checked_out_today
                        ? "Checked out"
                        : "Checked in"
                      : "Not checked in"}
                  </p>
                  {e.checked_in_today && checkInTime && (
                    <p className="text-xs opacity-80">
                      {checkInTime}
                      {mode ? ` · ${mode}` : ""}
                    </p>
                  )}
                </div>
              </div>

              <p className="mt-2 text-sm text-slate-500">{e.work_email}</p>
              {reportsTo && (
                <p className="mt-2 text-xs text-slate-400">
                  {isPeers ? (
                    <span className="text-slate-600">{reportsTo}</span>
                  ) : (
                    <>
                      Reports to: <span className="text-slate-600">{reportsTo}</span>
                    </>
                  )}
                </p>
              )}
              <p className="mt-2 text-xs capitalize text-green-600">{e.employment_status}</p>
            </Card>
          );
        })}
        {!team?.length && (
          <Card className="sm:col-span-2 lg:col-span-3">
            <p className="text-sm text-slate-500">
              No team members yet. You&apos;ll see your reportees here, or teammates who report to the same manager.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
