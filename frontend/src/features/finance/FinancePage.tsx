import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { IndianRupee, Wallet } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Can } from "@/components/Can";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface Compensation {
  id: string;
  employee_id: string;
  ctc: string | null;
  ctc_annual: number | null;
  designation: string | null;
  joining_date: string | null;
  gross_monthly: number | null;
  net_monthly: number | null;
  earnings: Record<string, number>;
  deductions: Record<string, number>;
  source: string;
}

interface MyPayData {
  configured: boolean;
  compensation: Compensation | null;
  payslip_count: number;
  message: string | null;
}

interface Payslip {
  id: string;
  month: number;
  year: number;
  gross_pay: number;
  net_pay: number;
  earnings: Record<string, number>;
  deductions: Record<string, number>;
}

interface Category { id: string; name: string }
interface Claim { id: string; category_id: string; amount: number; expense_date: string; status: string; description: string | null }
interface Employee { id: string; first_name: string; last_name: string; employee_code: string; work_email: string | null }

const SOURCE_LABELS: Record<string, string> = {
  offer_letter: "From released offer letter",
  admin: "Configured by HR / Admin",
};

function formatCurrency(n: number | null | undefined) {
  if (n == null) return "—";
  return `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function FinancePage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"my-pay" | "payslips" | "expenses" | "admin">("my-pay");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ category_id: "", amount: "", expense_date: "", description: "" });
  const [error, setError] = useState("");
  const [adminEmployeeId, setAdminEmployeeId] = useState("");
  const [adminForm, setAdminForm] = useState({ ctc: "", designation: "", joining_date: "" });
  const [adminMessage, setAdminMessage] = useState("");

  const { data: myPay } = useQuery({
    queryKey: ["my-pay"],
    queryFn: () => apiRequest<MyPayData>("/api/v1/finance/my-pay", { token: accessToken }),
    enabled: tab === "my-pay",
  });

  const { data: payslips } = useQuery({
    queryKey: ["payslips"],
    queryFn: () => apiRequest<Payslip[]>("/api/v1/finance/payslips", { token: accessToken }),
    enabled: tab === "payslips",
  });

  const { data: categories } = useQuery({
    queryKey: ["reimbursement-categories"],
    queryFn: () => apiRequest<Category[]>("/api/v1/finance/reimbursements/categories", { token: accessToken }),
  });

  const { data: claims } = useQuery({
    queryKey: ["reimbursements"],
    queryFn: () =>
      apiRequest<{ items: Claim[] }>("/api/v1/finance/reimbursements", { token: accessToken }),
    enabled: tab === "expenses",
  });

  const { data: employees } = useQuery({
    queryKey: ["employees-pay-admin"],
    queryFn: () => apiRequest<{ items: Employee[] }>("/api/v1/employees?page_size=100", { token: accessToken }),
    enabled: tab === "admin",
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/finance/reimbursements", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ ...form, amount: parseFloat(form.amount) }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reimbursements"] });
      setShowForm(false);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const saveCompMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/finance/compensation/${adminEmployeeId}`, {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify({
          ctc: adminForm.ctc,
          designation: adminForm.designation || null,
          joining_date: adminForm.joining_date || null,
        }),
      }),
    onSuccess: () => {
      setAdminMessage("Pay details saved for employee.");
      queryClient.invalidateQueries({ queryKey: ["my-pay"] });
    },
    onError: (err: Error) => setAdminMessage(err.message),
  });

  const monthName = (m: number) => new Date(2000, m - 1).toLocaleString("default", { month: "long" });
  const comp = myPay?.compensation;

  return (
    <div className="space-y-6">
      <PageHeader title="My Pay" description="Compensation, payslips, and expense claims" />

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-1">
        {([
          ["my-pay", "My Pay"],
          ["payslips", "Payslips"],
          ["expenses", "Expenses"],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              tab === key ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800",
            )}
          >
            {label}
          </button>
        ))}
        <Can permission="payroll.process">
          <button
            type="button"
            onClick={() => setTab("admin")}
            className={cn(
              "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              tab === "admin" ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800",
            )}
          >
            Configure Pay (Admin)
          </button>
        </Can>
      </div>

      {tab === "my-pay" && (
        <>
          {!myPay?.configured ? (
            <Card className="border-brand-100 bg-brand-50/50">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                  <Wallet className="h-6 w-6" />
                </div>
                <div>
                  <p className="font-semibold text-slate-900">Pay details not available yet</p>
                  <p className="mt-1 text-sm text-slate-600">{myPay?.message}</p>
                  <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">
                    <li>HR admin can configure CTC manually under <strong>Configure Pay (Admin)</strong></li>
                    <li>Or it auto-syncs when an offer letter is <strong>released</strong> to your work/login email</li>
                  </ul>
                </div>
              </div>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Card className="bg-gradient-to-br from-brand-500 to-brand-700 text-white">
                  <p className="text-sm text-white/80">Annual CTC</p>
                  <p className="mt-1 text-2xl font-bold">{comp?.ctc ?? "—"}</p>
                  {comp?.ctc_annual && (
                    <p className="mt-1 text-xs text-white/70">{formatCurrency(comp.ctc_annual)} / year</p>
                  )}
                </Card>
                <Card>
                  <p className="text-sm text-slate-500">Monthly Gross</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">{formatCurrency(comp?.gross_monthly)}</p>
                </Card>
                <Card>
                  <p className="text-sm text-slate-500">Monthly Net (est.)</p>
                  <p className="mt-1 text-2xl font-bold text-green-700">{formatCurrency(comp?.net_monthly)}</p>
                </Card>
                <Card>
                  <p className="text-sm text-slate-500">Designation</p>
                  <p className="mt-1 text-lg font-semibold text-slate-900">{comp?.designation ?? "—"}</p>
                  {comp?.joining_date && (
                    <p className="mt-1 text-xs text-slate-500">Joined {comp.joining_date}</p>
                  )}
                </Card>
              </div>

              <p className="text-xs text-slate-400">
                Source: {SOURCE_LABELS[comp?.source ?? ""] ?? comp?.source}
              </p>

              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader title="Monthly Earnings" />
                  <dl className="space-y-2 text-sm">
                    {Object.entries(comp?.earnings ?? {}).map(([key, val]) => (
                      <div key={key} className="flex justify-between border-b border-slate-50 py-2">
                        <dt className="capitalize text-slate-600">{key.replace(/_/g, " ")}</dt>
                        <dd className="font-medium">{formatCurrency(val)}</dd>
                      </div>
                    ))}
                  </dl>
                </Card>
                <Card>
                  <CardHeader title="Monthly Deductions (est.)" />
                  <dl className="space-y-2 text-sm">
                    {Object.entries(comp?.deductions ?? {}).map(([key, val]) => (
                      <div key={key} className="flex justify-between border-b border-slate-50 py-2">
                        <dt className="capitalize text-slate-600">{key.replace(/_/g, " ")}</dt>
                        <dd className="font-medium text-red-600">{formatCurrency(val)}</dd>
                      </div>
                    ))}
                  </dl>
                </Card>
              </div>
            </>
          )}

          <Card>
            <CardHeader title="Payslips" description={`${myPay?.payslip_count ?? 0} payslips on file`} />
            <p className="text-sm text-slate-500">
              View detailed monthly payslips in the <button type="button" className="text-brand-600 hover:underline" onClick={() => setTab("payslips")}>Payslips tab</button>.
            </p>
          </Card>
        </>
      )}

      {tab === "payslips" && (
        <Card>
          <CardHeader title="Payslip History" />
          {payslips?.length ? payslips.map((p) => (
            <div key={p.id} className="mb-4 rounded-lg border border-slate-200 p-4">
              <div className="flex justify-between">
                <p className="font-medium">{monthName(p.month)} {p.year}</p>
                <p className="font-bold text-brand-700">{formatCurrency(p.net_pay)}</p>
              </div>
              <p className="mt-1 text-sm text-slate-500">Gross: {formatCurrency(p.gross_pay)}</p>
            </div>
          )) : (
            <p className="text-sm text-slate-500">No payslips processed yet. Your CTC and breakdown appear under My Pay.</p>
          )}
        </Card>
      )}

      {tab === "expenses" && (
        <>
          <div className="flex justify-end">
            <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "New Claim"}</Button>
          </div>
          {showForm && (
            <Card>
              <CardHeader title="Submit Reimbursement" />
              <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); submitMutation.mutate(); }}>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">Category</label>
                  <select className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" required
                    value={form.category_id} onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}>
                    <option value="">Select</option>
                    {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <Input label="Amount" type="number" step="0.01" required value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
                <Input label="Expense Date" type="date" required value={form.expense_date}
                  onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))} />
                <Input label="Description" value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
                {error && <p className="text-sm text-red-600">{error}</p>}
                <Button type="submit" disabled={submitMutation.isPending}>Submit</Button>
              </form>
            </Card>
          )}
          <Card>
            <CardHeader title="My Claims" />
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-slate-500">
                <th className="pb-2">Date</th><th className="pb-2">Amount</th><th className="pb-2">Status</th>
              </tr></thead>
              <tbody>
                {claims?.items.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100">
                    <td className="py-2">{c.expense_date}</td>
                    <td className="py-2">{formatCurrency(c.amount)}</td>
                    <td className="py-2 capitalize">{c.status}</td>
                  </tr>
                ))}
                {!claims?.items.length && (
                  <tr><td colSpan={3} className="py-4 text-center text-slate-500">No claims yet</td></tr>
                )}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {tab === "admin" && (
        <Card>
          <CardHeader
            title="Configure Employee Pay"
            description="Set CTC manually or it auto-syncs when a matching offer letter is released"
          />
          {adminMessage && (
            <p className="mb-4 rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700">{adminMessage}</p>
          )}
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (!adminEmployeeId) return;
              saveCompMutation.mutate();
            }}
          >
            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Employee</label>
              <select
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                required
                value={adminEmployeeId}
                onChange={(e) => setAdminEmployeeId(e.target.value)}
              >
                <option value="">Select employee...</option>
                {employees?.items.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.first_name} {emp.last_name} ({emp.employee_code}) — {emp.work_email}
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="CTC"
              required
              placeholder="e.g. 15 LPA or 1500000"
              value={adminForm.ctc}
              onChange={(e) => setAdminForm((f) => ({ ...f, ctc: e.target.value }))}
            />
            <Input
              label="Designation"
              value={adminForm.designation}
              onChange={(e) => setAdminForm((f) => ({ ...f, designation: e.target.value }))}
            />
            <Input
              label="Joining Date"
              type="date"
              value={adminForm.joining_date}
              onChange={(e) => setAdminForm((f) => ({ ...f, joining_date: e.target.value }))}
            />
            <div className="flex items-end sm:col-span-2">
              <Button type="submit" disabled={saveCompMutation.isPending || !adminEmployeeId}>
                <IndianRupee className="mr-2 h-4 w-4" />
                {saveCompMutation.isPending ? "Saving..." : "Save Pay Details"}
              </Button>
            </div>
          </form>
          <p className="mt-4 text-xs text-slate-500">
            Tip: When creating an offer letter, use the candidate&apos;s work email. Releasing the offer will auto-fill their My Pay.
          </p>
        </Card>
      )}
    </div>
  );
}
