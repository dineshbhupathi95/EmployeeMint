import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { apiRequest } from "@/api/client";
import { Can } from "@/components/Can";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface Employee {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  work_email: string | null;
  employment_status: string;
  phone: string | null;
  role_ids?: string[];
  leave_type_ids?: string[];
  reports_to_employee_id?: string | null;
}

interface Role {
  id: string;
  name: string;
}

interface LeaveType {
  id: string;
  name: string;
  code: string;
  annual_quota: number;
}

const emptyForm = {
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  work_email: "",
  phone: "",
  role_ids: [] as string[],
  leave_type_ids: [] as string[],
  reports_to_employee_id: "" as string,
};

export function EmployeesPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");

  const { data } = useQuery({
    queryKey: ["employees"],
    queryFn: () =>
      apiRequest<{ items: Employee[] }>("/api/v1/employees?page_size=100", { token: accessToken }),
  });

  const { data: nextCode } = useQuery({
    queryKey: ["employees-next-code"],
    queryFn: () =>
      apiRequest<{ employee_code: string }>("/api/v1/employees/next-code", { token: accessToken }),
    enabled: modal === "create",
  });

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: () => apiRequest<Role[]>("/api/v1/roles", { token: accessToken }),
    enabled: modal !== null,
  });

  const { data: leaveTypes } = useQuery({
    queryKey: ["leave-types"],
    queryFn: () => apiRequest<LeaveType[]>("/api/v1/leave/types", { token: accessToken }),
    enabled: modal !== null,
  });

  const managerOptions = useMemo(
    () => (data?.items ?? []).filter((e) => e.id !== editing?.id),
    [data?.items, editing?.id],
  );

  const selectedLeaveSummary = useMemo(() => {
    const selected = (leaveTypes ?? []).filter((t) => form.leave_type_ids.includes(t.id));
    const total = selected.reduce((sum, t) => sum + Number(t.annual_quota), 0);
    return { selected, total };
  }, [leaveTypes, form.leave_type_ids]);

  const managerName = (id: string | null | undefined) => {
    if (!id) return "—";
    const mgr = data?.items.find((e) => e.id === id);
    return mgr ? `${mgr.first_name} ${mgr.last_name}` : "—";
  };

  const toggleLeaveType = (id: string) => {
    setForm((f) => ({
      ...f,
      leave_type_ids: f.leave_type_ids.includes(id)
        ? f.leave_type_ids.filter((x) => x !== id)
        : [...f.leave_type_ids, id],
    }));
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const reportsTo = form.reports_to_employee_id || null;
      if (modal === "edit" && editing) {
        return apiRequest(`/api/v1/employees/${editing.id}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify({
            first_name: form.first_name,
            last_name: form.last_name,
            work_email: form.work_email || null,
            phone: form.phone || null,
            role_ids: form.role_ids,
            leave_type_ids: form.leave_type_ids,
            reports_to_employee_id: reportsTo,
          }),
        });
      }
      return apiRequest("/api/v1/employees", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
          password: form.password,
          work_email: form.work_email || form.email,
          phone: form.phone || null,
          role_ids: form.role_ids,
          leave_type_ids: form.leave_type_ids,
          reports_to_employee_id: reportsTo,
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["employees-next-code"] });
      queryClient.invalidateQueries({ queryKey: ["leave-balances"] });
      setModal(null);
      setEditing(null);
      setForm(emptyForm);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const openCreate = () => {
    setForm(emptyForm);
    setEditing(null);
    setModal("create");
    setError("");
  };
  const openEdit = (e: Employee) => {
    setEditing(e);
    setForm({
      ...emptyForm,
      first_name: e.first_name,
      last_name: e.last_name,
      work_email: e.work_email || "",
      phone: e.phone || "",
      email: e.work_email || "",
      role_ids: e.role_ids ?? [],
      leave_type_ids: e.leave_type_ids ?? [],
      reports_to_employee_id: e.reports_to_employee_id ?? "",
    });
    setModal("edit");
    setError("");
  };

  return (
    <div>
      <PageHeader
        title="Employees"
        description="Create and manage employee records"
        action={
          <Can permission="employee.create">
            <Button onClick={openCreate}>+ Add Employee</Button>
          </Can>
        }
      />
      <Card>
        <CardHeader title="All Employees" />
        <div className="overflow-x-auto">
          <table className="em-table">
            <thead>
              <tr>
                <th>Employee ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Manager</th>
                <th>Leaves</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((e) => (
                <tr key={e.id}>
                  <td className="font-mono text-xs text-slate-600">{e.employee_code}</td>
                  <td className="font-medium text-slate-900">
                    {e.first_name} {e.last_name}
                  </td>
                  <td>{e.work_email}</td>
                  <td>{managerName(e.reports_to_employee_id)}</td>
                  <td>{e.leave_type_ids?.length ?? 0} types</td>
                  <td className="capitalize">{e.employment_status}</td>
                  <td>
                    <Can permission="employee.edit.all">
                      <button onClick={() => openEdit(e)} className="text-brand-600 hover:underline">
                        Edit
                      </button>
                    </Can>
                  </td>
                </tr>
              ))}
              {!data?.items.length && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-slate-500">
                    No employees found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal
        open={modal !== null}
        onClose={() => setModal(null)}
        title={modal === "edit" ? "Edit Employee" : "Add Employee"}
        wide
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            saveMutation.mutate();
          }}
        >
          {modal === "create" && (
            <>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-sm font-medium text-slate-700">Employee ID</p>
                <p className="mt-1 font-mono text-brand-700">
                  {nextCode?.employee_code ?? "Generating..."}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Auto-generated from tenant slug (e.g. ACME-001, ACME-002)
                </p>
              </div>
              <Input
                label="Login Email"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
              <Input
                label="Password"
                type="password"
                required
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              />
            </>
          )}
          {modal === "edit" && editing && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-sm font-medium text-slate-700">Employee ID</p>
              <p className="mt-1 font-mono text-brand-700">{editing.employee_code}</p>
            </div>
          )}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Role</label>
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              required
              value={form.role_ids[0] ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, role_ids: e.target.value ? [e.target.value] : [] }))
              }
            >
              <option value="">Select role</option>
              {roles?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">
              Reporting Manager / Team Lead
            </label>
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={form.reports_to_employee_id}
              onChange={(e) => setForm((f) => ({ ...f, reports_to_employee_id: e.target.value }))}
            >
              <option value="">No manager</option>
              {managerOptions.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.first_name} {e.last_name} ({e.employee_code})
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="First Name"
              required
              value={form.first_name}
              onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
            />
            <Input
              label="Last Name"
              required
              value={form.last_name}
              onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
            />
          </div>
          <Input
            label="Work Email"
            value={form.work_email}
            onChange={(e) => setForm((f) => ({ ...f, work_email: e.target.value }))}
          />
          <Input
            label="Phone"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />

          <div>
            <div className="mb-1.5 flex items-baseline justify-between gap-3">
              <label className="block text-sm font-medium text-slate-700">
                Applicable leave types
              </label>
              <span className="text-xs text-slate-500">
                {selectedLeaveSummary.selected.length} selected · {selectedLeaveSummary.total} days /
                year
              </span>
            </div>
            {!leaveTypes?.length ? (
              <p className="rounded-lg border border-dashed border-slate-200 px-3 py-4 text-sm text-slate-500">
                No leave types configured. Add them under Settings → Leave Types.
              </p>
            ) : (
              <div className="max-h-52 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
                {leaveTypes.map((t) => {
                  const checked = form.leave_type_ids.includes(t.id);
                  return (
                    <label
                      key={t.id}
                      className={cn(
                        "flex cursor-pointer items-center justify-between gap-3 rounded-md px-3 py-2 text-sm",
                        checked ? "bg-brand-50 text-brand-900" : "hover:bg-slate-50",
                      )}
                    >
                      <span className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="rounded border-slate-300"
                          checked={checked}
                          onChange={() => toggleLeaveType(t.id)}
                        />
                        <span>
                          <span className="font-medium">{t.name}</span>
                          <span className="ml-1.5 text-xs text-slate-400">{t.code}</span>
                        </span>
                      </span>
                      <span className="shrink-0 text-xs font-medium text-slate-600">
                        {Number(t.annual_quota)} days
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
            {selectedLeaveSummary.selected.length > 0 && (
              <div className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                <p className="font-medium text-slate-700">Leave entitlement preview</p>
                <ul className="mt-1 space-y-0.5">
                  {selectedLeaveSummary.selected.map((t) => (
                    <li key={t.id} className="flex justify-between gap-2">
                      <span>{t.name}</span>
                      <span>{Number(t.annual_quota)} available</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-3">
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Saving..." : "Save"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => setModal(null)}>
              Cancel
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
