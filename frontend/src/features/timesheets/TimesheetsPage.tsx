import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface Entry {
  id: string;
  work_date: string;
  hours: number;
  description: string;
  status: string;
}

const statusColor: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

const statusHint: Record<string, string> = {
  draft: "Not submitted yet",
  pending: "Waiting for manager approval",
  approved: "Approved by manager",
  rejected: "Rejected — edit and resubmit",
};

export function TimesheetsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Entry | null>(null);
  const [form, setForm] = useState({ work_date: "", hours: "8", description: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const { data, isError, error: queryError } = useQuery({
    queryKey: ["timesheets"],
    queryFn: () => apiRequest<{ items: Entry[] }>("/api/v1/timesheets", { token: accessToken }),
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const body = {
        work_date: form.work_date,
        hours: parseFloat(form.hours),
        description: form.description,
      };
      if (editing) {
        return apiRequest(`/api/v1/timesheets/${editing.id}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify(body),
        });
      }
      return apiRequest("/api/v1/timesheets", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timesheets"] });
      setShowForm(false);
      setEditing(null);
      setForm({ work_date: "", hours: "8", description: "" });
      setError("");
      setMessage("Timesheet entry saved.");
    },
    onError: (err: Error) => setError(err.message),
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/timesheets/${id}/submit`, { method: "POST", token: accessToken }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timesheets"] });
      setMessage("Submitted for manager approval. Check Approvals inbox (manager view).");
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const openEdit = (e: Entry) => {
    setEditing(e);
    setForm({ work_date: e.work_date, hours: String(e.hours), description: e.description });
    setShowForm(true);
  };

  const items = data?.items ?? [];
  const totalHours = items.filter((e) => e.status === "approved").reduce((s, e) => s + Number(e.hours), 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Timesheets"
        description="Log hours, submit for approval, track manager decisions"
        action={
          <Button
            onClick={() => {
              setEditing(null);
              setForm({ work_date: "", hours: "8", description: "" });
              setShowForm(true);
            }}
          >
            + Log Hours
          </Button>
        }
      />

      {message && (
        <p className="rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700">{message}</p>
      )}
      {(error || (isError && queryError)) && (
        <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
          {error || (queryError instanceof Error ? queryError.message : "Failed to load timesheets")}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="bg-gradient-to-br from-brand-500 to-brand-700 text-white">
          <p className="text-sm text-white/80">Approved Hours</p>
          <p className="mt-1 text-3xl font-bold">{totalHours}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Pending Approval</p>
          <p className="mt-1 text-3xl font-bold text-amber-600">
            {items.filter((e) => e.status === "pending").length}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Draft Entries</p>
          <p className="mt-1 text-3xl font-bold text-slate-700">
            {items.filter((e) => e.status === "draft").length}
          </p>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="My Timesheet Entries"
          description="Draft → Submit → Manager approves in Approvals"
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-max text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="pb-2 pr-4">Date</th>
                <th className="pb-2 pr-4">Hours</th>
                <th className="pb-2 pr-4">Description</th>
                <th className="pb-2 pr-4">Status</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-b border-slate-100">
                  <td className="py-3 pr-4">{e.work_date}</td>
                  <td className="py-3 pr-4 font-medium">{e.hours}h</td>
                  <td className="py-3 pr-4 text-slate-600">{e.description}</td>
                  <td className="py-3 pr-4">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                        statusColor[e.status] ?? "",
                      )}
                    >
                      {e.status}
                    </span>
                    <p className="mt-0.5 text-[10px] text-slate-400">{statusHint[e.status]}</p>
                  </td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-2">
                      {(e.status === "draft" || e.status === "rejected") && (
                        <>
                          <button
                            type="button"
                            onClick={() => openEdit(e)}
                            className="text-brand-600 hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => submitMutation.mutate(e.id)}
                            disabled={submitMutation.isPending}
                            className="inline-flex items-center gap-1 text-green-600 hover:underline"
                          >
                            <Send className="h-3 w-3" />
                            Submit for Approval
                          </button>
                        </>
                      )}
                      {e.status === "pending" && (
                        <span className="text-xs text-amber-600">In manager inbox</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {!items.length && !isError && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No timesheet entries yet. Click &quot;+ Log Hours&quot; to add one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? "Edit Entry" : "Log Hours"}>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            saveMutation.mutate();
          }}
        >
          <Input
            label="Work Date"
            type="date"
            required
            value={form.work_date}
            onChange={(e) => setForm((f) => ({ ...f, work_date: e.target.value }))}
          />
          <Input
            label="Hours"
            type="number"
            step="0.5"
            min="0.5"
            max="24"
            required
            value={form.hours}
            onChange={(e) => setForm((f) => ({ ...f, hours: e.target.value }))}
          />
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Description</label>
            <textarea
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              rows={3}
              required
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving..." : "Save"}
          </Button>
        </form>
      </Modal>
    </div>
  );
}
