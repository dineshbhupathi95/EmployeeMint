import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { PlatformLayout } from "@/features/platform/PlatformLayout";
import type { TenantAdmin, TenantDetail } from "@/features/platform/types";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-3 text-sm last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-900">{value}</span>
    </div>
  );
}

function AdminEditForm({
  tenantId,
  admin,
  onCancel,
  onSaved,
}: {
  tenantId: string;
  admin: TenantAdmin;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [form, setForm] = useState({
    email: admin.email,
    first_name: admin.first_name || "",
    last_name: admin.last_name || "",
    password: "",
    is_active: admin.is_active,
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {
        email: form.email,
        first_name: form.first_name,
        last_name: form.last_name,
        is_active: form.is_active,
      };
      if (form.password) body.password = form.password;
      return apiRequest<TenantAdmin>(
        `/api/v1/platform/tenants/${tenantId}/admins/${admin.user_id}`,
        { method: "PATCH", token: accessToken, body: JSON.stringify(body) },
      );
    },
    onSuccess: () => {
      onSaved();
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <form
      className="mt-4 space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        setError("");
        mutation.mutate();
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="First name"
          value={form.first_name}
          onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
          required
        />
        <Input
          label="Last name"
          value={form.last_name}
          onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
          required
        />
      </div>
      <Input
        label="Email"
        type="email"
        value={form.email}
        onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
        required
      />
      <Input
        label="New password"
        type="password"
        placeholder="Leave blank to keep current password"
        value={form.password}
        onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
      />
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
          className="rounded border-slate-300"
        />
        Account active
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-3">
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving..." : "Save Admin"}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function TenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [editingTenant, setEditingTenant] = useState(false);
  const [editingAdminId, setEditingAdminId] = useState<string | null>(null);
  const [tenantError, setTenantError] = useState("");

  const { data: tenant, isLoading } = useQuery({
    queryKey: ["platform-tenant", tenantId],
    queryFn: () =>
      apiRequest<TenantDetail>(`/api/v1/platform/tenants/${tenantId}`, {
        token: accessToken,
      }),
    enabled: !!tenantId,
  });

  const [tenantForm, setTenantForm] = useState({
    name: "",
    plan: "starter",
    max_employees: 100,
    is_active: true,
    is_setup_complete: false,
  });

  const startTenantEdit = () => {
    if (!tenant) return;
    setTenantForm({
      name: tenant.name,
      plan: tenant.plan,
      max_employees: tenant.max_employees,
      is_active: tenant.is_active,
      is_setup_complete: tenant.is_setup_complete,
    });
    setEditingTenant(true);
    setTenantError("");
  };

  const tenantMutation = useMutation({
    mutationFn: () =>
      apiRequest<TenantDetail>(`/api/v1/platform/tenants/${tenantId}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify(tenantForm),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["platform-tenant", tenantId], data);
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
      setEditingTenant(false);
      setTenantError("");
    },
    onError: (err: Error) => setTenantError(err.message),
  });

  if (isLoading || !tenant) {
    return (
      <PlatformLayout>
        <p className="text-slate-500">{isLoading ? "Loading tenant..." : "Tenant not found."}</p>
      </PlatformLayout>
    );
  }

  return (
    <PlatformLayout>
      <div className="mb-6">
        <Link to="/platform/tenants" className="text-sm text-brand-600 hover:underline">
          ← Back to tenants
        </Link>
        <div className="mt-3 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">{tenant.name}</h2>
            <p className="text-slate-500">
              {tenant.slug} · {tenant.employee_count} employees
            </p>
          </div>
          {!editingTenant && (
            <Button variant="secondary" onClick={startTenantEdit}>
              Edit Tenant
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Tenant Details" description="Organization configuration and status" />
          {editingTenant ? (
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                tenantMutation.mutate();
              }}
            >
              <Input
                label="Company name"
                value={tenantForm.name}
                onChange={(e) => setTenantForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">Plan</label>
                <select
                  value={tenantForm.plan}
                  onChange={(e) => setTenantForm((f) => ({ ...f, plan: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="starter">Starter</option>
                  <option value="growth">Growth</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <Input
                label="Max employees"
                type="number"
                min={1}
                value={tenantForm.max_employees}
                onChange={(e) =>
                  setTenantForm((f) => ({ ...f, max_employees: Number(e.target.value) }))
                }
                required
              />
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={tenantForm.is_active}
                  onChange={(e) => setTenantForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-slate-300"
                />
                Tenant active
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={tenantForm.is_setup_complete}
                  onChange={(e) =>
                    setTenantForm((f) => ({ ...f, is_setup_complete: e.target.checked }))
                  }
                  className="rounded border-slate-300"
                />
                Setup complete
              </label>
              {tenantError && <p className="text-sm text-red-600">{tenantError}</p>}
              <div className="flex gap-3">
                <Button type="submit" disabled={tenantMutation.isPending}>
                  {tenantMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => setEditingTenant(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            <div>
              <DetailRow label="Slug" value={tenant.slug} />
              <DetailRow label="Plan" value={<span className="capitalize">{tenant.plan}</span>} />
              <DetailRow label="Max employees" value={tenant.max_employees} />
              <DetailRow label="Employees" value={tenant.employee_count} />
              <DetailRow
                label="Status"
                value={
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      tenant.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}
                  >
                    {tenant.is_active ? "Active" : "Suspended"}
                  </span>
                }
              />
              <DetailRow
                label="Setup"
                value={tenant.is_setup_complete ? "Complete" : "Pending"}
              />
              <DetailRow label="Custom domain" value={tenant.custom_domain || "—"} />
              <DetailRow label="Created" value={formatDate(tenant.created_at)} />
              <DetailRow label="Updated" value={formatDate(tenant.updated_at)} />
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            title="Org Admins"
            description="Manage organization administrators for this tenant"
          />
          {tenant.admins.length === 0 ? (
            <p className="text-sm text-slate-500">No org admins found.</p>
          ) : (
            <div className="space-y-4">
              {tenant.admins.map((admin) => (
                <div key={admin.user_id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-slate-900">
                        {[admin.first_name, admin.last_name].filter(Boolean).join(" ") || "—"}
                      </p>
                      <p className="text-sm text-slate-600">{admin.email}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {admin.role_name} · Last login: {formatDate(admin.last_login_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          admin.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {admin.is_active ? "Active" : "Inactive"}
                      </span>
                      {editingAdminId !== admin.user_id && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setEditingAdminId(admin.user_id)}
                        >
                          Edit
                        </Button>
                      )}
                    </div>
                  </div>
                  {editingAdminId === admin.user_id && (
                    <AdminEditForm
                      tenantId={tenant.id}
                      admin={admin}
                      onCancel={() => setEditingAdminId(null)}
                      onSaved={() => {
                        setEditingAdminId(null);
                        queryClient.invalidateQueries({ queryKey: ["platform-tenant", tenantId] });
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </PlatformLayout>
  );
}
