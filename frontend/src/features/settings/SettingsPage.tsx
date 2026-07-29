import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";

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

export function SettingsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"holidays" | "leave" | "roles" | "workflows" | "announcements">("holidays");

  const [holidayForm, setHolidayForm] = useState({ name: "", date: "" });
  const [editHoliday, setEditHoliday] = useState<Holiday | null>(null);

  const [leaveForm, setLeaveForm] = useState({ name: "", code: "", annual_quota: "12" });
  const [editLeave, setEditLeave] = useState<LeaveType | null>(null);

  const [annForm, setAnnForm] = useState({ title: "", body: "" });
  const [editAnn, setEditAnn] = useState<Announcement | null>(null);

  const [roleModal, setRoleModal] = useState(false);
  const [editRole, setEditRole] = useState<Role | null>(null);
  const [roleForm, setRoleForm] = useState({ name: "", description: "", permission_codes: [] as string[] });

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
    enabled: tab === "roles",
  });

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
    { id: "holidays" as const, label: "Holidays" },
    { id: "leave" as const, label: "Leave Types" },
    { id: "roles" as const, label: "Roles & Permissions" },
    { id: "workflows" as const, label: "Workflows" },
    { id: "announcements" as const, label: "Announcements" },
  ];

  const permsByModule = matrix?.permissions.reduce<Record<string, Permission[]>>((acc, p) => {
    (acc[p.module] ??= []).push(p);
    return acc;
  }, {}) ?? {};

  return (
    <div>
      <PageHeader title="Settings" description="Configure policies, roles, and workflows" />

      <div className="mb-6 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Button key={t.id} variant={tab === t.id ? "primary" : "secondary"} onClick={() => setTab(t.id)}>
            {t.label}
          </Button>
        ))}
      </div>

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
