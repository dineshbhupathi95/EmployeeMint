import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  CheckCircle2,
  Clock,
  Home,
  Receipt,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface ApprovalStep {
  id: string;
  step_order: number;
  status: string;
  comments: string | null;
}

interface ApprovalRequest {
  id: string;
  request_type: string;
  requester_name: string | null;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
  steps: ApprovalStep[];
}

const TYPE_CONFIG: Record<
  string,
  { label: string; icon: typeof Clock; color: string; bg: string }
> = {
  leave: { label: "Leave", icon: Calendar, color: "text-blue-700", bg: "bg-blue-50" },
  timesheet: { label: "Timesheet", icon: Clock, color: "text-brand-700", bg: "bg-brand-50" },
  wfh: { label: "Work From Home", icon: Home, color: "text-violet-700", bg: "bg-violet-50" },
  reimbursement: { label: "Reimbursement", icon: Receipt, color: "text-amber-700", bg: "bg-amber-50" },
  regularization: {
    label: "Attendance Fix",
    icon: Clock,
    color: "text-slate-700",
    bg: "bg-slate-100",
  },
};

function formatPayload(type: string, payload: Record<string, unknown>): string {
  switch (type) {
    case "leave":
      return `${payload.start_date ?? "?"} → ${payload.end_date ?? "?"} (${payload.days ?? "?"} days)`;
    case "timesheet":
      return `${payload.hours ?? "?"} hours on ${payload.date ?? "?"}${payload.description ? ` — ${payload.description}` : ""}`;
    case "wfh":
      return `Date: ${payload.date ?? "?"}${payload.reason ? ` — ${payload.reason}` : ""}`;
    case "reimbursement":
      return `${payload.amount ?? "?"} — ${payload.description ?? "Expense claim"}`;
    case "regularization":
      return `Date: ${payload.date ?? "?"}${payload.reason ? ` — ${payload.reason}` : ""}`;
    default:
      return Object.entries(payload)
        .map(([k, v]) => `${k}: ${String(v)}`)
        .join(" · ");
  }
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-amber-100 text-amber-800",
    approved: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
  };
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium capitalize", styles[status] ?? styles.pending)}>
      {status}
    </span>
  );
}

function ApprovalCard({
  req,
  onApprove,
  onReject,
  rejectId,
  comment,
  setComment,
  setRejectId,
  isPending,
}: {
  req: ApprovalRequest;
  onApprove: (stepId: string) => void;
  onReject: (stepId: string) => void;
  rejectId: string | null;
  comment: string;
  setComment: (v: string) => void;
  setRejectId: (v: string | null) => void;
  isPending: boolean;
}) {
  const step = req.steps.find((s) => s.status === "pending");
  if (!step) return null;

  const config = TYPE_CONFIG[req.request_type] ?? {
    label: req.request_type,
    icon: Clock,
    color: "text-slate-700",
    bg: "bg-slate-100",
  };
  const Icon = config.icon;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start gap-4">
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl", config.bg, config.color)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-slate-900">{config.label} Request</h3>
            <StatusBadge status="pending" />
          </div>
          <p className="mt-1 text-sm font-medium text-slate-700">
            {req.requester_name ?? "Employee"}
          </p>
          <p className="mt-1 text-sm text-slate-600">{formatPayload(req.request_type, req.payload)}</p>
          <p className="mt-2 text-xs text-slate-400">
            Submitted {new Date(req.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      {rejectId === step.id ? (
        <div className="mt-4 rounded-lg border border-red-100 bg-red-50/50 p-4">
          <Input
            label="Rejection reason (required)"
            placeholder="Explain why this request is rejected..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => { setRejectId(null); setComment(""); }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => onReject(step.id)}
              disabled={!comment.trim() || isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              Confirm Reject
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex gap-2 border-t border-slate-100 pt-4">
          <Button size="sm" onClick={() => onApprove(step.id)} disabled={isPending}>
            <CheckCircle2 className="mr-1.5 h-4 w-4" />
            Approve
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setRejectId(step.id)}>
            <XCircle className="mr-1.5 h-4 w-4" />
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

export function ApprovalsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"inbox" | "history">("inbox");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [comment, setComment] = useState("");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["approvals-inbox"] });
    queryClient.invalidateQueries({ queryKey: ["approvals-history"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    queryClient.invalidateQueries({ queryKey: ["timesheets"] });
  };

  const { data: inbox, isLoading: inboxLoading } = useQuery({
    queryKey: ["approvals-inbox"],
    queryFn: () => apiRequest<ApprovalRequest[]>("/api/v1/approvals/inbox", { token: accessToken }),
  });

  const { data: history } = useQuery({
    queryKey: ["approvals-history"],
    queryFn: () => apiRequest<ApprovalRequest[]>("/api/v1/approvals/history", { token: accessToken }),
    enabled: tab === "history",
  });

  const act = (stepId: string, action: "approve" | "reject") =>
    apiRequest(`/api/v1/approvals/steps/${stepId}/${action}`, {
      method: "POST",
      token: accessToken,
      body: JSON.stringify({ comments: action === "reject" ? comment : undefined }),
    });

  const approveMutation = useMutation({
    mutationFn: (stepId: string) => act(stepId, "approve"),
    onSuccess: () => { invalidate(); setRejectId(null); setComment(""); },
  });

  const rejectMutation = useMutation({
    mutationFn: (stepId: string) => act(stepId, "reject"),
    onSuccess: () => { setRejectId(null); setComment(""); invalidate(); },
  });

  const isPending = approveMutation.isPending || rejectMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description={`${inbox?.length ?? 0} request${(inbox?.length ?? 0) === 1 ? "" : "s"} awaiting your action`}
      />

      <div className="flex gap-2 border-b border-slate-200">
        {(["inbox", "history"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "border-b-2 px-4 py-2 text-sm font-medium capitalize transition-colors",
              tab === t
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-800",
            )}
          >
            {t === "inbox" ? `Pending (${inbox?.length ?? 0})` : "History"}
          </button>
        ))}
      </div>

      {tab === "inbox" && (
        <div className="space-y-4">
          {inboxLoading && <p className="text-sm text-slate-500">Loading approvals...</p>}
          {inbox?.map((req) => (
            <ApprovalCard
              key={req.id}
              req={req}
              rejectId={rejectId}
              comment={comment}
              setComment={setComment}
              setRejectId={setRejectId}
              isPending={isPending}
              onApprove={(id) => approveMutation.mutate(id)}
              onReject={(id) => rejectMutation.mutate(id)}
            />
          ))}
          {!inboxLoading && !inbox?.length && (
            <Card className="py-12 text-center">
              <CheckCircle2 className="mx-auto h-10 w-10 text-green-500" />
              <p className="mt-3 font-medium text-slate-900">All caught up!</p>
              <p className="mt-1 text-sm text-slate-500">No pending approvals in your inbox.</p>
            </Card>
          )}
        </div>
      )}

      {tab === "history" && (
        <Card>
          <CardHeader title="Recent Decisions" description="Last 50 approved or rejected requests" />
          <div className="overflow-x-auto">
            <table className="w-full min-w-max text-left text-sm">
              <thead>
                <tr className="border-b text-slate-500">
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Employee</th>
                  <th className="pb-2 pr-4">Details</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {history?.map((r) => {
                  const config = TYPE_CONFIG[r.request_type];
                  return (
                    <tr key={r.id} className="border-b border-slate-100">
                      <td className="py-3 pr-4 font-medium capitalize">
                        {config?.label ?? r.request_type}
                      </td>
                      <td className="py-3 pr-4 text-slate-700">{r.requester_name ?? "—"}</td>
                      <td className="py-3 pr-4 text-slate-600">{formatPayload(r.request_type, r.payload)}</td>
                      <td className="py-3 pr-4"><StatusBadge status={r.status} /></td>
                      <td className="py-3 text-slate-500">{new Date(r.created_at).toLocaleDateString()}</td>
                    </tr>
                  );
                })}
                {!history?.length && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">No history yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
