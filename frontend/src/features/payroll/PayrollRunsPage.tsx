import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Plus,
  RefreshCw,
  Send,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiDownload, apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAnyPermission } from "@/hooks/usePermission";
import { useAuthStore } from "@/store/auth";

interface PayrollRun {
  id: string;
  month: number;
  year: number;
  status: string;
  notes: string | null;
  finance_notes: string | null;
  total_gross: number;
  total_net: number;
  employee_count: number;
}

interface PayrollLine {
  id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  base_gross: number;
  lop_days: number;
  lop_amount: number;
  bonus: number;
  other_earnings: Record<string, number>;
  other_deductions: Record<string, number>;
  gross_pay: number;
  total_deductions: number;
  net_pay: number;
  leave_summary: Record<string, number>;
  bank_snapshot: Record<string, string>;
  payment_status: string | null;
  notes: string | null;
}

interface PayrollRunDetail extends PayrollRun {
  lines: PayrollLine[];
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  submitted: "bg-amber-100 text-amber-800",
  rejected: "bg-red-100 text-red-800",
  approved: "bg-blue-100 text-blue-800",
  processing: "bg-violet-100 text-violet-800",
  completed: "bg-green-100 text-green-800",
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function formatCurrency(n: number | null | undefined) {
  if (n == null) return "—";
  return `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium capitalize", STATUS_STYLES[status] ?? STATUS_STYLES.draft)}>
      {status}
    </span>
  );
}

export function PayrollRunsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canDraft = useAnyPermission(["payroll.draft", "payroll.process"]);
  const canSubmit = useAnyPermission(["payroll.submit", "payroll.process"]);
  const canApprove = useAnyPermission(["payroll.approve", "payroll.process"]);
  const canExport = useAnyPermission(["payroll.export", "payroll.process"]);
  const canImport = useAnyPermission(["payroll.import", "payroll.process"]);
  const canFinalize = useAnyPermission(["payroll.finalize", "payroll.process"]);
  const canViewPayroll = useAnyPermission([
    "payroll.draft", "payroll.submit", "payroll.approve", "payroll.view.all",
    "payroll.process", "payroll.export", "payroll.import", "payroll.finalize",
  ]);

  const now = new Date();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createMonth, setCreateMonth] = useState(now.getMonth() + 1);
  const [createYear, setCreateYear] = useState(now.getFullYear());
  const [showCreate, setShowCreate] = useState(false);
  const [message, setMessage] = useState("");
  const [rejectNotes, setRejectNotes] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [editingLine, setEditingLine] = useState<string | null>(null);
  const [lineForm, setLineForm] = useState({
    lop_days: "",
    bonus: "",
    other_earning_label: "",
    other_earning_amount: "",
    notes: "",
  });

  const { data: runs, isLoading } = useQuery({
    queryKey: ["payroll-runs"],
    queryFn: () => apiRequest<PayrollRun[]>("/api/v1/payroll/runs", { token: accessToken }),
    enabled: canViewPayroll,
  });

  useEffect(() => {
    if (!isLoading && runs?.length === 0 && canDraft) {
      setShowCreate(true);
    }
  }, [isLoading, runs?.length, canDraft]);

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["payroll-run", selectedId],
    queryFn: () => apiRequest<PayrollRunDetail>(`/api/v1/payroll/runs/${selectedId}`, { token: accessToken }),
    enabled: !!selectedId,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["payroll-runs"] });
    if (selectedId) queryClient.invalidateQueries({ queryKey: ["payroll-run", selectedId] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<PayrollRunDetail>("/api/v1/payroll/runs", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ month: createMonth, year: createYear }),
      }),
    onSuccess: (data) => {
      setShowCreate(false);
      setSelectedId(data.id);
      setMessage(`Draft created for ${MONTHS[createMonth - 1]} ${createYear} with ${data.employee_count} employees`);
      invalidate();
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const refreshMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/payroll/runs/${selectedId}/refresh`, { method: "POST", token: accessToken }),
    onSuccess: () => { setMessage("Refreshed with latest employees and leave data"); invalidate(); },
    onError: (err: Error) => setMessage(err.message),
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/payroll/runs/${selectedId}/submit`, { method: "POST", token: accessToken }),
    onSuccess: () => { setMessage("Submitted to Finance for review"); invalidate(); },
    onError: (err: Error) => setMessage(err.message),
  });

  const approveMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/payroll/runs/${selectedId}/approve`, { method: "POST", token: accessToken }),
    onSuccess: () => { setMessage("Payroll approved — bank batch ready for export"); invalidate(); },
    onError: (err: Error) => setMessage(err.message),
  });

  const rejectMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/payroll/runs/${selectedId}/reject`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ finance_notes: rejectNotes }),
      }),
    onSuccess: () => { setShowReject(false); setRejectNotes(""); setMessage("Returned to HR with notes"); invalidate(); },
    onError: (err: Error) => setMessage(err.message),
  });

  const finalizeMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/payroll/runs/${selectedId}/finalize`, { method: "POST", token: accessToken }),
    onSuccess: () => { setMessage("Payroll finalized — payslips generated for all employees"); invalidate(); },
    onError: (err: Error) => setMessage(err.message),
  });

  const updateLineMutation = useMutation({
    mutationFn: (lineId: string) => {
      const other_earnings: Record<string, number> = {};
      if (lineForm.other_earning_label && lineForm.other_earning_amount) {
        other_earnings[lineForm.other_earning_label] = parseFloat(lineForm.other_earning_amount);
      }
      return apiRequest(`/api/v1/payroll/runs/${selectedId}/lines/${lineId}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({
          lop_days: lineForm.lop_days ? parseFloat(lineForm.lop_days) : undefined,
          bonus: lineForm.bonus ? parseFloat(lineForm.bonus) : undefined,
          other_earnings: Object.keys(other_earnings).length ? other_earnings : undefined,
          notes: lineForm.notes || undefined,
        }),
      });
    },
    onSuccess: () => {
      setEditingLine(null);
      invalidate();
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const handleExport = async () => {
    if (!selectedId) return;
    try {
      const blob = await apiDownload(`/api/v1/payroll/runs/${selectedId}/export`, accessToken);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `payroll_batch_${detail?.year}_${String(detail?.month).padStart(2, "0")}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      invalidate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Export failed");
    }
  };

  const handleUpload = async (file: File) => {
    if (!selectedId) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ""}/api/v1/payroll/runs/${selectedId}/upload-payment`,
        { method: "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: formData },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail?.error?.message ?? body?.error?.message ?? "Upload failed");
      }
      const result = await response.json();
      setMessage(result.message ?? "Payment status updated");
      invalidate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const openEditLine = (line: PayrollLine) => {
    setEditingLine(line.id);
    setLineForm({
      lop_days: String(line.lop_days),
      bonus: String(line.bonus),
      other_earning_label: Object.keys(line.other_earnings)[0] ?? "",
      other_earning_amount: String(Object.values(line.other_earnings)[0] ?? ""),
      notes: line.notes ?? "",
    });
  };

  const isEditable = detail?.status === "draft" || detail?.status === "rejected";

  if (!canViewPayroll) {
    return (
      <div className="space-y-6">
        <PageHeader title="Payroll Runs" description="Monthly payroll processing" />
        <Card>
          <CardHeader
            title="Access required"
            description="Your role does not have payroll permissions yet"
          />
          <p className="text-sm text-slate-600">
            Ask an Org Admin to assign payroll permissions (e.g.{" "}
            <code className="rounded bg-slate-100 px-1">payroll.draft</code>,{" "}
            <code className="rounded bg-slate-100 px-1">payroll.approve</code>) in{" "}
            <Link to="/app/settings" className="font-medium text-brand-700 hover:underline">
              Settings → Roles & Permissions
            </Link>
            , then log out and log back in.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Payroll Runs"
        description="Draft monthly payroll, submit for Finance review, export bank file, and generate payslips"
        action={
          canDraft ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Draft
            </Button>
          ) : undefined
        }
      />

      <Card className="border-slate-200 bg-slate-50/80">
        <p className="text-sm font-medium text-slate-800">How it works</p>
        <ol className="mt-2 grid gap-2 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-4">
          <li><span className="font-medium text-slate-700">1. HR</span> — Create draft, edit LOP/bonus</li>
          <li><span className="font-medium text-slate-700">2. HR</span> — Submit to Finance</li>
          <li><span className="font-medium text-slate-700">3. Finance</span> — Approve, export bank Excel</li>
          <li><span className="font-medium text-slate-700">4. Finance</span> — Upload payments, finalize payslips</li>
        </ol>
      </Card>

      {!canDraft && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          You can view payroll runs but cannot create drafts. HR needs{" "}
          <code className="rounded bg-amber-100 px-1">payroll.draft</code> permission.
        </p>
      )}

      {message && (
        <p className="rounded-lg bg-brand-50 px-4 py-2 text-sm text-brand-800">{message}</p>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-1">
          <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Payroll Draft">
            <p className="mb-4 text-sm text-slate-600">
              Auto-populates all active employees with compensation, leave (LOP), and bank details.
            </p>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Month</label>
                <select
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={createMonth}
                  onChange={(e) => setCreateMonth(parseInt(e.target.value))}
                >
                  {MONTHS.map((m, i) => (
                    <option key={m} value={i + 1}>{m}</option>
                  ))}
                </select>
              </div>
              <Input
                label="Year"
                type="number"
                value={createYear}
                onChange={(e) => setCreateYear(parseInt(e.target.value))}
              />
              <Button
                className="w-full"
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create Draft"}
              </Button>
            </div>
          </Modal>

          <Card>
            <CardHeader title="Payroll Runs" />
            {isLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : runs?.length ? (
              <div className="space-y-2">
                {runs.map((run) => (
                  <button
                    key={run.id}
                    type="button"
                    onClick={() => setSelectedId(run.id)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-colors",
                      selectedId === run.id ? "border-brand-500 bg-brand-50" : "border-slate-200 hover:bg-slate-50",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{MONTHS[run.month - 1]} {run.year}</span>
                      <StatusBadge status={run.status} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {run.employee_count} employees · Net {formatCurrency(run.total_net)}
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-3 py-2 text-center">
                <p className="text-sm text-slate-500">No payroll runs yet.</p>
                {canDraft && (
                  <Button onClick={() => setShowCreate(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    Create your first draft
                  </Button>
                )}
              </div>
            )}
          </Card>
        </div>

        <div className="lg:col-span-2">
          {!selectedId ? (
            <Card>
              <p className="text-sm text-slate-500">Select a payroll run to view details and take action.</p>
            </Card>
          ) : detailLoading ? (
            <Card><p className="text-sm text-slate-500">Loading...</p></Card>
          ) : detail ? (
            <div className="space-y-4">
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold">{MONTHS[detail.month - 1]} {detail.year}</h2>
                    <StatusBadge status={detail.status} />
                    {detail.finance_notes && (
                      <p className="mt-2 text-sm text-red-600">Finance notes: {detail.finance_notes}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {isEditable && canDraft && (
                      <Button variant="secondary" size="sm" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
                        <RefreshCw className="mr-1 h-4 w-4" /> Refresh
                      </Button>
                    )}
                    {isEditable && canSubmit && (
                      <Button size="sm" onClick={() => submitMutation.mutate()} disabled={submitMutation.isPending}>
                        <Send className="mr-1 h-4 w-4" /> Submit to Finance
                      </Button>
                    )}
                    {detail.status === "submitted" && canApprove && (
                      <>
                        <Button size="sm" onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}>
                          <CheckCircle2 className="mr-1 h-4 w-4" /> Approve
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => setShowReject(true)}>
                          <XCircle className="mr-1 h-4 w-4" /> Reject
                        </Button>
                      </>
                    )}
                    {["approved", "processing"].includes(detail.status) && canExport && (
                      <Button variant="secondary" size="sm" onClick={handleExport}>
                        <Download className="mr-1 h-4 w-4" /> Export Bank File
                      </Button>
                    )}
                    {["approved", "processing"].includes(detail.status) && canImport && (
                      <>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".xlsx,.xls"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleUpload(file);
                            e.target.value = "";
                          }}
                        />
                        <Button variant="secondary" size="sm" onClick={() => fileInputRef.current?.click()}>
                          <Upload className="mr-1 h-4 w-4" /> Upload Payment Status
                        </Button>
                      </>
                    )}
                    {["approved", "processing"].includes(detail.status) && canFinalize && (
                      <Button size="sm" onClick={() => finalizeMutation.mutate()} disabled={finalizeMutation.isPending}>
                        <FileSpreadsheet className="mr-1 h-4 w-4" /> Finalize & Generate Payslips
                      </Button>
                    )}
                  </div>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                  <div>
                    <p className="text-xs text-slate-500">Employees</p>
                    <p className="text-lg font-semibold">{detail.employee_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Total Gross</p>
                    <p className="text-lg font-semibold">{formatCurrency(detail.total_gross)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Total Net</p>
                    <p className="text-lg font-semibold text-green-700">{formatCurrency(detail.total_net)}</p>
                  </div>
                </div>
              </Card>

              {showReject && (
                <Card>
                  <CardHeader title="Reject Payroll" description="Return to HR with feedback" />
                  <textarea
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    rows={3}
                    placeholder="Reason for rejection..."
                    value={rejectNotes}
                    onChange={(e) => setRejectNotes(e.target.value)}
                  />
                  <div className="mt-3 flex gap-2">
                    <Button onClick={() => rejectMutation.mutate()} disabled={!rejectNotes.trim() || rejectMutation.isPending}>
                      Confirm Reject
                    </Button>
                    <Button variant="secondary" onClick={() => setShowReject(false)}>Cancel</Button>
                  </div>
                </Card>
              )}

              {editingLine && (
                <Card>
                  <CardHeader title="Edit Employee Line" description="Adjust LOP, bonus, and other earnings" />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input label="LOP Days" type="number" step="0.5" value={lineForm.lop_days}
                      onChange={(e) => setLineForm((f) => ({ ...f, lop_days: e.target.value }))} />
                    <Input label="Bonus" type="number" step="0.01" value={lineForm.bonus}
                      onChange={(e) => setLineForm((f) => ({ ...f, bonus: e.target.value }))} />
                    <Input label="Other Earning Label" placeholder="e.g. incentive" value={lineForm.other_earning_label}
                      onChange={(e) => setLineForm((f) => ({ ...f, other_earning_label: e.target.value }))} />
                    <Input label="Other Earning Amount" type="number" value={lineForm.other_earning_amount}
                      onChange={(e) => setLineForm((f) => ({ ...f, other_earning_amount: e.target.value }))} />
                    <div className="sm:col-span-2">
                      <Input label="Notes" value={lineForm.notes}
                        onChange={(e) => setLineForm((f) => ({ ...f, notes: e.target.value }))} />
                    </div>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Button onClick={() => updateLineMutation.mutate(editingLine)} disabled={updateLineMutation.isPending}>
                      Save Line
                    </Button>
                    <Button variant="secondary" onClick={() => setEditingLine(null)}>Cancel</Button>
                  </div>
                </Card>
              )}

              <Card>
                <CardHeader title="Employee Lines" description={isEditable ? "Click a row to edit LOP, bonus, and adjustments" : "Read-only view"} />
                <div className="overflow-x-auto">
                  <table className="em-table text-sm">
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Name</th>
                        <th>Gross</th>
                        <th>LOP</th>
                        <th>Bonus</th>
                        <th>Net</th>
                        <th>Bank</th>
                        <th>Payment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.lines.map((line) => (
                        <tr
                          key={line.id}
                          className={cn(isEditable && "cursor-pointer hover:bg-slate-50")}
                          onClick={() => isEditable && openEditLine(line)}
                        >
                          <td>{line.employee_code}</td>
                          <td>{line.employee_name}</td>
                          <td className="tabular-nums">{formatCurrency(line.base_gross)}</td>
                          <td className="tabular-nums">
                            {line.lop_days > 0 ? `${line.lop_days}d (-${formatCurrency(line.lop_amount)})` : "—"}
                          </td>
                          <td className="tabular-nums">{line.bonus > 0 ? formatCurrency(line.bonus) : "—"}</td>
                          <td className="tabular-nums font-medium">{formatCurrency(line.net_pay)}</td>
                          <td className="text-xs">
                            {line.bank_snapshot?.account_number
                              ? `${line.bank_snapshot.bank_name} ···${line.bank_snapshot.account_number.slice(-4)}`
                              : <span className="text-amber-600">Missing</span>}
                          </td>
                          <td className="capitalize">{line.payment_status ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
