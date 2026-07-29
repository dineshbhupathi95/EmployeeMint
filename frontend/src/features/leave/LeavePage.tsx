import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";

interface LeaveType { id: string; name: string; code: string; annual_quota: number }
interface LeaveBalance {
  leave_type_id: string;
  leave_type_name?: string | null;
  leave_type_code?: string | null;
  allocated: number;
  used: number;
  pending: number;
  available: number;
}
interface LeaveRequest {
  id: string; start_date: string; end_date: string; days: number; status: string;
  reason: string | null; leave_type_id: string; is_half_day: boolean;
}

const emptyForm = { leave_type_id: "", start_date: "", end_date: "", reason: "", is_half_day: false };

export function LeavePage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<LeaveRequest | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");

  const { data: types } = useQuery({
    queryKey: ["leave-types"],
    queryFn: () => apiRequest<LeaveType[]>("/api/v1/leave/types", { token: accessToken }),
  });

  const { data: balances } = useQuery({
    queryKey: ["leave-balances"],
    queryFn: () => apiRequest<LeaveBalance[]>("/api/v1/leave/balances", { token: accessToken }),
  });

  const { data: requests } = useQuery({
    queryKey: ["leave-requests"],
    queryFn: () =>
      apiRequest<{ items: LeaveRequest[] }>("/api/v1/leave/requests", { token: accessToken }),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    queryClient.invalidateQueries({ queryKey: ["leave-balances"] });
  };

  const applyMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/leave/requests", {
        method: "POST", token: accessToken, body: JSON.stringify(form),
      }),
    onSuccess: () => { invalidate(); setShowForm(false); setForm(emptyForm); setError(""); },
    onError: (err: Error) => setError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/leave/requests/${editing!.id}`, {
        method: "PATCH", token: accessToken, body: JSON.stringify(form),
      }),
    onSuccess: () => { invalidate(); setEditing(null); setForm(emptyForm); setError(""); },
    onError: (err: Error) => setError(err.message),
  });

  const typeName = (id: string) =>
    balances?.find((b) => b.leave_type_id === id)?.leave_type_name
    ?? types?.find((t) => t.id === id)?.name
    ?? id;

  const applicableTypes = (balances ?? []).map((b) => ({
    id: b.leave_type_id,
    name: b.leave_type_name || types?.find((t) => t.id === b.leave_type_id)?.name || b.leave_type_id,
    available: b.available,
    allocated: b.allocated,
  }));

  const openEdit = (r: LeaveRequest) => {
    setEditing(r);
    setForm({
      leave_type_id: r.leave_type_id,
      start_date: r.start_date,
      end_date: r.end_date,
      reason: r.reason || "",
      is_half_day: r.is_half_day,
    });
    setError("");
  };

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-amber-100 text-amber-700",
      approved: "bg-green-100 text-green-700",
      rejected: "bg-red-100 text-red-700",
    };
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${styles[status] ?? "bg-slate-100 text-slate-600"}`}>
        {status}
      </span>
    );
  };

  const LeaveForm = ({ onSubmit, submitLabel }: { onSubmit: () => void; submitLabel: string }) => (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700">Leave Type</label>
        <select className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" required
          value={form.leave_type_id} onChange={(e) => setForm((f) => ({ ...f, leave_type_id: e.target.value }))}>
          <option value="">Select type</option>
          {applicableTypes.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.available} available of {t.allocated})
            </option>
          ))}
        </select>
        {!applicableTypes.length && (
          <p className="mt-1 text-xs text-amber-700">
            No leave types assigned. Ask HR to set applicable leaves on your employee profile.
          </p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input label="Start Date" type="date" required value={form.start_date}
          onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))} />
        <Input label="End Date" type="date" required value={form.end_date}
          onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))} />
      </div>
      <Input label="Reason" value={form.reason} onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.is_half_day}
          onChange={(e) => setForm((f) => ({ ...f, is_half_day: e.target.checked }))} />
        Half day
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit">{submitLabel}</Button>
    </form>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leave"
        description="Apply, edit pending requests, or reapply after rejection"
        action={<Button onClick={() => { setShowForm(!showForm); setForm(emptyForm); setError(""); }}>
          {showForm ? "Cancel" : "Apply Leave"}
        </Button>}
      />

      <div className="grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {balances?.map((b) => (
          <Card key={b.leave_type_id} className="min-w-0">
            <p className="truncate text-sm text-slate-500">{typeName(b.leave_type_id)}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{Number(b.available)}</p>
            <p className="text-xs text-slate-400">
              of {Number(b.allocated)} days · {Number(b.used)} used · {Number(b.pending)} pending
            </p>
          </Card>
        ))}
        {!balances?.length && (
          <Card className="sm:col-span-2 lg:col-span-3">
            <p className="text-sm text-slate-600">No leave balances yet.</p>
            <p className="mt-1 text-xs text-slate-400">
              HR must assign applicable leave types when creating or editing your employee record.
            </p>
          </Card>
        )}
      </div>

      {showForm && (
        <Card>
          <CardHeader title="Apply for Leave" />
          <LeaveForm onSubmit={() => applyMutation.mutate()} submitLabel={applyMutation.isPending ? "Submitting..." : "Submit Request"} />
        </Card>
      )}

      <Card>
        <CardHeader title="Leave History" description="Edit pending requests or reapply rejected ones" />
        <div className="overflow-x-auto">
          <table className="em-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Dates</th>
                <th>Days</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests?.items.map((r) => (
                <tr key={r.id}>
                  <td>{typeName(r.leave_type_id)}</td>
                  <td className="whitespace-nowrap">{r.start_date} → {r.end_date}</td>
                  <td className="tabular-nums">{r.days}{r.is_half_day ? " (½)" : ""}</td>
                  <td>{statusBadge(r.status)}</td>
                  <td>
                    {(r.status === "pending" || r.status === "rejected") && (
                      <button onClick={() => openEdit(r)} className="text-brand-600 hover:underline">
                        {r.status === "rejected" ? "Edit & Reapply" : "Edit"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!requests?.items.length && (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-slate-500">
                    No leave requests yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal
        open={editing !== null}
        onClose={() => { setEditing(null); setError(""); }}
        title={editing?.status === "rejected" ? "Edit & Reapply Leave" : "Edit Leave Request"}
      >
        {editing && (
          <>
            {editing.status === "rejected" && (
              <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                This request was rejected. Saving will resubmit it to your manager for approval.
              </p>
            )}
            <LeaveForm
              onSubmit={() => updateMutation.mutate()}
              submitLabel={updateMutation.isPending ? "Saving..." : editing.status === "rejected" ? "Reapply" : "Save Changes"}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
