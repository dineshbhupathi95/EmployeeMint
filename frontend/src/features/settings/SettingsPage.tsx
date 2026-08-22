import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, ImagePlus, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { useAuthStore, type UserInfo } from "@/store/auth";
import { useAnyPermission } from "@/hooks/usePermission";
import { AiAssistantSettings } from "@/features/settings/AiAssistantSettings";

interface Holiday { id: string; name: string; date: string; is_optional: boolean }
interface LeaveType { id: string; name: string; code: string; annual_quota: number }
interface Workflow { id: string; name: string; request_type: string; is_active: boolean; steps: { step_order: number; approver_rule: string }[] }
interface Announcement {
  id: string;
  title: string;
  body: string;
  is_pinned: boolean;
  show_on_dashboard: boolean;
}
interface Permission { id: string; code: string; name: string; module: string }
interface Role { id: string; name: string; description: string | null; is_system: boolean; permissions: Permission[] }

interface Branding {
  name: string;
  slug: string;
  has_logo: boolean;
}

interface PayrollSettings {
  working_days_per_month: number;
  hr_roles: string[];
  finance_roles: string[];
  admin_roles: string[];
}

export function SettingsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  const canManageBranding = useAnyPermission(["settings.manage", "org.manage"]);
  const canManageAi = useAnyPermission(["assistant.manage", "settings.manage", "*"]);
  const [tab, setTab] = useState<
    "branding" | "holidays" | "leave" | "roles" | "workflows" | "announcements" | "assistant" | "payroll"
  >("branding");

  const [orgName, setOrgName] = useState("");
  const [brandMsg, setBrandMsg] = useState("");
  const [brandErr, setBrandErr] = useState("");
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);

  const [holidayForm, setHolidayForm] = useState({ name: "", date: "" });
  const [editHoliday, setEditHoliday] = useState<Holiday | null>(null);

  const [leaveForm, setLeaveForm] = useState({ name: "", code: "", annual_quota: "12" });
  const [editLeave, setEditLeave] = useState<LeaveType | null>(null);

  const [annForm, setAnnForm] = useState({ title: "", body: "" });
  const [editAnn, setEditAnn] = useState<Announcement | null>(null);

  const [roleModal, setRoleModal] = useState(false);
  const [editRole, setEditRole] = useState<Role | null>(null);
  const [roleForm, setRoleForm] = useState({ name: "", description: "", permission_codes: [] as string[] });
  const [payrollSettings, setPayrollSettings] = useState<PayrollSettings>({
    working_days_per_month: 30,
    hr_roles: ["HR Admin", "HR Executive"],
    finance_roles: ["Finance Admin"],
    admin_roles: ["Org Admin"],
  });
  const [payrollMsg, setPayrollMsg] = useState("");

  const refreshMe = async () => {
    const me = await apiRequest<UserInfo>("/api/v1/auth/me", { token: accessToken });
    setUser(me);
  };

  const { data: branding } = useQuery({
    queryKey: ["branding"],
    queryFn: () => apiRequest<Branding>("/api/v1/settings/branding", { token: accessToken }),
    enabled: tab === "branding",
  });

  useEffect(() => {
    if (branding) setOrgName(branding.name);
  }, [branding]);

  useEffect(() => {
    let url: string | null = null;
    let cancelled = false;
    async function loadLogo() {
      if (!branding?.has_logo || !accessToken) {
        setLogoPreview(null);
        return;
      }
      try {
        const { apiDownload } = await import("@/api/client");
        const blob = await apiDownload("/api/v1/settings/branding/logo", accessToken);
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setLogoPreview(url);
      } catch {
        if (!cancelled) setLogoPreview(null);
      }
    }
    loadLogo();
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [branding?.has_logo, accessToken, branding?.name]);

  const { data: holidays } = useQuery({
    queryKey: ["holidays"],
    queryFn: () => apiRequest<Holiday[]>("/api/v1/settings/holidays", { token: accessToken }),
    enabled: tab === "holidays",
  });

  const { data: leaveTypes } = useQuery({
    queryKey: ["settings-leave-types"],
    queryFn: () => apiRequest<LeaveType[]>("/api/v1/settings/leave-types", { token: accessToken }),
    enabled: tab === "leave",
  });

  const { data: matrix } = useQuery({
    queryKey: ["roles-matrix"],
    queryFn: () => apiRequest<{ permissions: Permission[]; roles: Role[] }>("/api/v1/roles/matrix", { token: accessToken }),
    enabled: tab === "roles" || tab === "payroll",
  });

  const { data: payrollSettingsData } = useQuery({
    queryKey: ["payroll-settings"],
    queryFn: () => apiRequest<PayrollSettings>("/api/v1/payroll/settings", { token: accessToken }),
    enabled: tab === "payroll",
  });

  useEffect(() => {
    if (payrollSettingsData) setPayrollSettings(payrollSettingsData);
  }, [payrollSettingsData]);

  const { data: workflows } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => apiRequest<Workflow[]>("/api/v1/settings/workflows", { token: accessToken }),
    enabled: tab === "workflows",
  });

  const { data: announcements } = useQuery({
    queryKey: ["announcements"],
    queryFn: () => apiRequest<Announcement[]>("/api/v1/settings/announcements", { token: accessToken }),
    enabled: tab === "announcements",
  });

  const invalidate = (keys: string[]) => keys.forEach((k) => queryClient.invalidateQueries({ queryKey: [k] }));

  const saveBranding = useMutation({
    mutationFn: () =>
      apiRequest<Branding>("/api/v1/settings/branding", {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify({ name: orgName }),
      }),
    onSuccess: async () => {
      setBrandErr("");
      setBrandMsg("Organization name updated.");
      invalidate(["branding"]);
      await refreshMe();
      setTimeout(() => setBrandMsg(""), 3000);
    },
    onError: (e: Error) => setBrandErr(e.message),
  });

  const uploadLogo = async (file: File | null) => {
    if (!file) return;
    setLogoBusy(true);
    setBrandErr("");
    setBrandMsg("");
    try {
      const form = new FormData();
      form.append("file", file);
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
      const res = await fetch(`${API_BASE}/api/v1/settings/branding/logo`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const msg =
          body?.detail?.error?.message ||
          body?.error?.message ||
          res.statusText ||
          "Upload failed";
        throw new Error(msg);
      }
      setBrandMsg("Logo uploaded.");
      invalidate(["branding"]);
      await refreshMe();
      setTimeout(() => setBrandMsg(""), 3000);
    } catch (e) {
      setBrandErr(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLogoBusy(false);
      if (logoInputRef.current) logoInputRef.current.value = "";
    }
  };

  const removeLogo = useMutation({
    mutationFn: () =>
      apiRequest<Branding>("/api/v1/settings/branding/logo", {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: async () => {
      setBrandMsg("Logo removed.");
      invalidate(["branding"]);
      await refreshMe();
      setTimeout(() => setBrandMsg(""), 3000);
    },
    onError: (e: Error) => setBrandErr(e.message),
  });

  const addHoliday = useMutation({
    mutationFn: () => apiRequest("/api/v1/settings/holidays", { method: "POST", token: accessToken, body: JSON.stringify(holidayForm) }),
    onSuccess: () => { invalidate(["holidays"]); setHolidayForm({ name: "", date: "" }); },
  });

  const updateHoliday = useMutation({
    mutationFn: () => apiRequest(`/api/v1/settings/holidays/${editHoliday!.id}`, { method: "PATCH", token: accessToken, body: JSON.stringify(editHoliday) }),
    onSuccess: () => { invalidate(["holidays"]); setEditHoliday(null); },
  });

  const addLeaveType = useMutation({
    mutationFn: () => apiRequest("/api/v1/settings/leave-types", {
      method: "POST", token: accessToken,
      body: JSON.stringify({ ...leaveForm, annual_quota: parseFloat(leaveForm.annual_quota) }),
    }),
    onSuccess: () => { invalidate(["settings-leave-types"]); setLeaveForm({ name: "", code: "", annual_quota: "12" }); },
  });

  const updateLeaveType = useMutation({
    mutationFn: () => apiRequest(`/api/v1/settings/leave-types/${editLeave!.id}`, {
      method: "PATCH", token: accessToken,
      body: JSON.stringify({ name: editLeave!.name, code: editLeave!.code, annual_quota: editLeave!.annual_quota }),
    }),
    onSuccess: () => { invalidate(["settings-leave-types"]); setEditLeave(null); },
  });

  const saveRole = useMutation({
    mutationFn: () => {
      const body = { name: roleForm.name, description: roleForm.description || null, permission_codes: roleForm.permission_codes };
      if (editRole) {
        return apiRequest(`/api/v1/roles/${editRole.id}`, { method: "PATCH", token: accessToken, body: JSON.stringify(body) });
      }
      return apiRequest("/api/v1/roles", { method: "POST", token: accessToken, body: JSON.stringify(body) });
    },
    onSuccess: () => { invalidate(["roles-matrix", "roles"]); setRoleModal(false); setEditRole(null); },
  });

  const savePayrollSettings = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/payroll/settings", {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify(payrollSettings),
      }),
    onSuccess: () => {
      setPayrollMsg("Payroll settings saved");
      invalidate(["payroll-settings"]);
    },
    onError: (err: Error) => setPayrollMsg(err.message),
  });

  const togglePayrollRole = (field: "hr_roles" | "finance_roles" | "admin_roles", roleName: string) => {
    setPayrollSettings((prev) => {
      const current = prev[field];
      return {
        ...prev,
        [field]: current.includes(roleName)
          ? current.filter((r) => r !== roleName)
          : [...current, roleName],
      };
    });
  };

  const addAnnouncement = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/settings/announcements", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ ...annForm, show_on_dashboard: true }),
      }),
    onSuccess: () => {
      invalidate(["announcements", "dashboard-summary"]);
      setAnnForm({ title: "", body: "" });
    },
  });

  const updateAnnouncement = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/settings/announcements/${editAnn!.id}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({
          title: editAnn!.title,
          body: editAnn!.body,
          is_pinned: editAnn!.is_pinned,
          show_on_dashboard: editAnn!.show_on_dashboard,
        }),
      }),
    onSuccess: () => {
      invalidate(["announcements", "dashboard-summary"]);
      setEditAnn(null);
    },
  });

  const toggleDashboardVisibility = useMutation({
    mutationFn: (a: Announcement) =>
      apiRequest(`/api/v1/settings/announcements/${a.id}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ show_on_dashboard: a.show_on_dashboard === false }),
      }),
    onSuccess: () => invalidate(["announcements", "dashboard-summary"]),
  });

  const openCreateRole = () => {
    setEditRole(null);
    setRoleForm({ name: "", description: "", permission_codes: [] });
    setRoleModal(true);
  };

  const openEditRole = (role: Role) => {
    setEditRole(role);
    setRoleForm({
      name: role.name,
      description: role.description || "",
      permission_codes: role.permissions.map((p) => p.code),
    });
    setRoleModal(true);
  };

  const togglePerm = (code: string) => {
    setRoleForm((f) => ({
      ...f,
      permission_codes: f.permission_codes.includes(code)
        ? f.permission_codes.filter((c) => c !== code)
        : [...f.permission_codes, code],
    }));
  };

  const tabs = [
    { id: "branding" as const, label: "Org name & logo" },
    { id: "holidays" as const, label: "Holidays" },
    { id: "leave" as const, label: "Leave Types" },
    { id: "roles" as const, label: "Roles & Permissions" },
    { id: "payroll" as const, label: "Payroll" },
    { id: "workflows" as const, label: "Workflows" },
    { id: "announcements" as const, label: "Announcements" },
    ...(canManageAi ? [{ id: "assistant" as const, label: "AI Assistant" }] : []),
  ];

  const permsByModule = matrix?.permissions.reduce<Record<string, Permission[]>>((acc, p) => {
    (acc[p.module] ??= []).push(p);
    return acc;
  }, {}) ?? {};

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Org name & logo, policies, roles, and workflows"
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Button key={t.id} variant={tab === t.id ? "primary" : "secondary"} onClick={() => setTab(t.id)}>
            {t.label}
          </Button>
        ))}
      </div>

      {tab === "branding" && (
        <Card>
          <CardHeader
            title="Organization name & logo"
            description="Shown in the left sidebar and top bar for everyone in this workspace"
          />
          <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                {logoPreview ? (
                  <img src={logoPreview} alt="Organization logo" className="h-full w-full object-contain p-1" />
                ) : (
                  <span className="text-lg font-bold text-brand-600">
                    {(orgName || "OR").slice(0, 2).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="min-w-0 flex-1 space-y-3">
                <p className="text-sm text-slate-600">JPG, PNG, WebP, or SVG · max 2MB</p>
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/svg+xml,.jpg,.jpeg,.png,.webp,.svg"
                  className="hidden"
                  onChange={(e) => uploadLogo(e.target.files?.[0] ?? null)}
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    disabled={logoBusy || !canManageBranding}
                    onClick={() => logoInputRef.current?.click()}
                  >
                    <ImagePlus className="mr-1.5 h-4 w-4" />
                    {logoBusy ? "Uploading…" : branding?.has_logo ? "Change logo" : "Upload logo"}
                  </Button>
                  {branding?.has_logo && (
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={removeLogo.isPending || !canManageBranding}
                      onClick={() => removeLogo.mutate()}
                    >
                      <Trash2 className="mr-1.5 h-4 w-4" />
                      Remove
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <form
              className="space-y-4 border-t border-slate-100 pt-4"
              onSubmit={(e) => {
                e.preventDefault();
                saveBranding.mutate();
              }}
            >
              <Input
                label="Organization name"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                disabled={!canManageBranding}
                placeholder="e.g. Acme Technologies"
              />
              {branding?.slug && (
                <p className="text-xs text-slate-500">
                  Workspace slug (login): <span className="font-mono">{branding.slug}</span>
                </p>
              )}
              {!canManageBranding && (
                <p className="text-sm text-amber-700">
                  You can view branding here. Ask an Org Admin or HR Admin to change the name or logo.
                </p>
              )}
              {brandErr && <p className="text-sm text-red-600">{brandErr}</p>}
              {brandMsg && <p className="text-sm text-green-600">{brandMsg}</p>}
              {canManageBranding && (
                <Button type="submit" disabled={saveBranding.isPending}>
                  {saveBranding.isPending ? "Saving…" : "Save organization name"}
                </Button>
              )}
            </form>
          </div>
        </Card>
      )}

      {tab === "holidays" && (
        <Card>
          <CardHeader title="Holiday Calendar" />
          <form className="em-form-row mb-4" onSubmit={(e) => { e.preventDefault(); addHoliday.mutate(); }}>
            <div className="min-w-[12rem] flex-1">
              <Input placeholder="Holiday name" value={holidayForm.name} onChange={(e) => setHolidayForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="w-44">
              <Input type="date" value={holidayForm.date} onChange={(e) => setHolidayForm((f) => ({ ...f, date: e.target.value }))} />
            </div>
            <Button type="submit">Add Holiday</Button>
          </form>
          <div className="overflow-x-auto">
            <table className="em-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Name</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {holidays?.map((h) => (
                  <tr key={h.id}>
                    <td className="whitespace-nowrap">{h.date}</td>
                    <td>{h.name}</td>
                    <td>
                      <button onClick={() => setEditHoliday({ ...h })} className="text-brand-600 hover:underline">Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "leave" && (
        <Card>
          <CardHeader title="Leave Types" />
          <form className="em-form-row mb-4" onSubmit={(e) => { e.preventDefault(); addLeaveType.mutate(); }}>
            <div className="min-w-[10rem] flex-1">
              <Input placeholder="Name" value={leaveForm.name} onChange={(e) => setLeaveForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="w-28">
              <Input placeholder="Code" value={leaveForm.code} onChange={(e) => setLeaveForm((f) => ({ ...f, code: e.target.value }))} />
            </div>
            <div className="w-28">
              <Input placeholder="Quota" type="number" value={leaveForm.annual_quota} onChange={(e) => setLeaveForm((f) => ({ ...f, annual_quota: e.target.value }))} />
            </div>
            <Button type="submit">Add Type</Button>
          </form>
          <div className="overflow-x-auto">
            <table className="em-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>Quota</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {leaveTypes?.map((t) => (
                  <tr key={t.id}>
                    <td>{t.name}</td>
                    <td>{t.code}</td>
                    <td>{t.annual_quota}</td>
                    <td>
                      <button onClick={() => setEditLeave({ ...t })} className="text-brand-600 hover:underline">Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "roles" && (
        <Card>
          <CardHeader
            title="Roles & Permissions"
            description="Create roles and assign permissions"
            action={<Button onClick={openCreateRole}>+ Create Role</Button>}
          />
          <div className="overflow-x-auto">
            <table className="em-table">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Permissions</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {matrix?.roles.map((role) => (
                  <tr key={role.id}>
                    <td className="font-medium text-slate-900">
                      {role.name}
                      {role.is_system && <span className="ml-2 text-xs font-normal text-slate-400">(system)</span>}
                    </td>
                    <td>{role.permissions.length} permissions</td>
                    <td>
                      <button onClick={() => openEditRole(role)} className="text-brand-600 hover:underline">Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "payroll" && (
        <Card>
          <CardHeader
            title="Payroll Settings"
            description="Configure LOP calculation and which roles can draft, review, and approve payroll runs"
          />
          {payrollMsg && <p className="mb-4 text-sm text-green-700">{payrollMsg}</p>}
          <form
            className="space-y-6"
            onSubmit={(e) => {
              e.preventDefault();
              savePayrollSettings.mutate();
            }}
          >
            <Input
              label="Working days per month (for LOP calculation)"
              type="number"
              min={20}
              max={31}
              value={payrollSettings.working_days_per_month}
              onChange={(e) =>
                setPayrollSettings((s) => ({ ...s, working_days_per_month: parseInt(e.target.value) || 30 }))
              }
            />
            {(["hr_roles", "finance_roles", "admin_roles"] as const).map((field) => (
              <div key={field}>
                <p className="mb-2 text-sm font-medium text-slate-700 capitalize">
                  {field.replace(/_/g, " ")}
                </p>
                <div className="flex flex-wrap gap-3">
                  {matrix?.roles.map((role) => (
                    <label key={role.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={payrollSettings[field].includes(role.name)}
                        onChange={() => togglePayrollRole(field, role.name)}
                        className="rounded"
                      />
                      {role.name}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-xs text-slate-500">
              Assign payroll permissions (payroll.draft, payroll.submit, payroll.approve, etc.) in Roles & Permissions.
              These role groups are used for payroll workflow routing and defaults.
            </p>
            <Button type="submit" disabled={savePayrollSettings.isPending}>
              {savePayrollSettings.isPending ? "Saving..." : "Save Payroll Settings"}
            </Button>
          </form>
        </Card>
      )}

      {tab === "workflows" && (
        <Card>
          <CardHeader title="Approval Workflows" />
          {workflows?.map((wf) => (
            <div key={wf.id} className="mb-4 rounded-lg border border-slate-200 p-4">
              <p className="font-medium">{wf.name} <span className="text-slate-400">({wf.request_type})</span></p>
              <ol className="mt-2 list-decimal pl-5 text-sm text-slate-600">
                {wf.steps.map((s) => <li key={s.step_order}>Step {s.step_order}: {s.approver_rule.replace(/_/g, " ")}</li>)}
              </ol>
            </div>
          ))}
        </Card>
      )}

      {tab === "announcements" && (
        <Card>
          <CardHeader
            title="Announcements"
            description="Publish updates. Use Show / Hide to control the dashboard ticker and announcements card."
          />
          <form className="mb-6 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4" onSubmit={(e) => { e.preventDefault(); addAnnouncement.mutate(); }}>
            <Input placeholder="Title" value={annForm.title} onChange={(e) => setAnnForm((f) => ({ ...f, title: e.target.value }))} />
            <textarea className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" rows={3} placeholder="Body"
              value={annForm.body} onChange={(e) => setAnnForm((f) => ({ ...f, body: e.target.value }))} />
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit">Publish</Button>
              <p className="text-xs text-slate-500">New announcements appear on the dashboard by default.</p>
            </div>
          </form>

          <div className="space-y-3">
            {!announcements?.length && (
              <p className="text-sm text-slate-500">No announcements yet. Publish one above.</p>
            )}
            {announcements?.map((a) => {
              const onDash = a.show_on_dashboard !== false;
              return (
                <div
                  key={a.id}
                  className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{a.title}</p>
                      <span
                        className={
                          onDash
                            ? "rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-green-800"
                            : "rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600"
                        }
                      >
                        {onDash ? "Visible on dashboard" : "Hidden from dashboard"}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500 line-clamp-2">{a.body}</p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <Button
                      type="button"
                      variant={onDash ? "secondary" : "primary"}
                      onClick={() => toggleDashboardVisibility.mutate(a)}
                      disabled={toggleDashboardVisibility.isPending}
                    >
                      {onDash ? (
                        <>
                          <EyeOff className="mr-1.5 h-4 w-4" />
                          Hide
                        </>
                      ) : (
                        <>
                          <Eye className="mr-1.5 h-4 w-4" />
                          Show
                        </>
                      )}
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => setEditAnn({ ...a, show_on_dashboard: onDash })}>
                      Edit
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {tab === "assistant" && canManageAi && <AiAssistantSettings />}

      {/* Edit modals */}
      <Modal open={!!editHoliday} onClose={() => setEditHoliday(null)} title="Edit Holiday">
        {editHoliday && (
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); updateHoliday.mutate(); }}>
            <Input label="Name" value={editHoliday.name} onChange={(e) => setEditHoliday((h) => h && { ...h, name: e.target.value })} />
            <Input label="Date" type="date" value={editHoliday.date} onChange={(e) => setEditHoliday((h) => h && { ...h, date: e.target.value })} />
            <Button type="submit">Save</Button>
          </form>
        )}
      </Modal>

      <Modal open={!!editLeave} onClose={() => setEditLeave(null)} title="Edit Leave Type">
        {editLeave && (
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); updateLeaveType.mutate(); }}>
            <Input label="Name" value={editLeave.name} onChange={(e) => setEditLeave((l) => l && { ...l, name: e.target.value })} />
            <Input label="Code" value={editLeave.code} onChange={(e) => setEditLeave((l) => l && { ...l, code: e.target.value })} />
            <Input label="Annual Quota" type="number" value={editLeave.annual_quota}
              onChange={(e) => setEditLeave((l) => l && { ...l, annual_quota: parseFloat(e.target.value) })} />
            <Button type="submit">Save</Button>
          </form>
        )}
      </Modal>

      <Modal open={!!editAnn} onClose={() => setEditAnn(null)} title="Edit Announcement">
        {editAnn && (
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); updateAnnouncement.mutate(); }}>
            <Input label="Title" value={editAnn.title} onChange={(e) => setEditAnn((a) => a && { ...a, title: e.target.value })} />
            <textarea className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" rows={4} value={editAnn.body}
              onChange={(e) => setEditAnn((a) => a && { ...a, body: e.target.value })} />
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                className="rounded border-slate-300"
                checked={editAnn.show_on_dashboard}
                onChange={(e) =>
                  setEditAnn((a) => a && { ...a, show_on_dashboard: e.target.checked })
                }
              />
              Show on dashboard
            </label>
            <Button type="submit">Save</Button>
          </form>
        )}
      </Modal>

      <Modal open={roleModal} onClose={() => setRoleModal(false)} title={editRole ? "Edit Role" : "Create Role"} wide>
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); saveRole.mutate(); }}>
          <Input label="Role Name" required value={roleForm.name} onChange={(e) => setRoleForm((f) => ({ ...f, name: e.target.value }))} />
          <Input label="Description" value={roleForm.description} onChange={(e) => setRoleForm((f) => ({ ...f, description: e.target.value }))} />
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Permissions</p>
            <div className="max-h-64 space-y-4 overflow-y-auto rounded-lg border border-slate-200 p-4">
              {Object.entries(permsByModule).map(([mod, perms]) => (
                <div key={mod}>
                  <p className="mb-2 text-xs font-semibold uppercase text-slate-400">{mod}</p>
                  <div className="grid grid-cols-2 gap-2">
                    {perms.map((p) => (
                      <label key={p.id} className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={roleForm.permission_codes.includes(p.code)}
                          onChange={() => togglePerm(p.code)} className="rounded" />
                        <span title={p.code}>{p.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <Button type="submit" disabled={saveRole.isPending}>{saveRole.isPending ? "Saving..." : "Save Role"}</Button>
        </form>
      </Modal>
    </div>
  );
}
